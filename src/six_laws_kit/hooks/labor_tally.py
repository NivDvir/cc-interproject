"""Stop hook: tally the head session's own tool calls for the turn that just finished. Reads one
JSON object from stdin (`session_id`, `transcript_path`), reads the transcript (a JSONL file,
newest records at the end), and writes `head-tally.<sid>` for the next `packet_reminder.py`
(UserPromptSubmit) run in the SAME session to pick up and print. This program is standalone: it
imports nothing from the `six_laws_kit` package, since it is copied alone to
`~/.claude/hooks/six-laws/`.

Sidechain records (sub-agent workers) are ignored entirely, so a transcript slice that is all
sidechain (a worker's own turn) never produces a tally. Among the remaining records, only the tool
calls made after the last plain user message (one with no `tool_result` block — the start of the
turn) are counted. `Agent`, `Task`, `SendMessage` and any `mcp__dispatch__start*` tool are folded
into a single `Delegate` count; everything else is counted and named individually, busiest first.

Exit code: always 0. Never raises. Prints nothing.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import time
from collections import Counter, deque
from pathlib import Path
from typing import Any

SID_MAX_LEN = 128
STATE_DIRNAME = "six-laws-state"
TAIL_LINES = 4000
STALE_SECONDS = 24 * 60 * 60
DELEGATION_NAMES = {"Agent", "Task", "SendMessage"}
DELEGATION_PREFIX = "mcp__dispatch__start"


def _sanitize_session_id(raw: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", raw)[:SID_MAX_LEN]


def _home_dir() -> Path:
    """An explicit `HOME` always wins over `Path.home()`, which on Windows reads `USERPROFILE`
    and ignores `HOME` entirely — so a caller sandboxing this hook by setting only `HOME` (as the
    installer and this repo's own tests do) would otherwise land outside the sandbox there.
    """
    override = os.environ.get("HOME")
    return Path(override) if override else Path.home()


def _state_dir() -> Path:
    path = _home_dir() / ".claude" / STATE_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _reap_stale(state_dir: Path) -> None:
    now = time.time()
    try:
        entries = list(state_dir.iterdir())
    except OSError:
        return
    for entry in entries:
        try:
            if entry.is_file() and (now - entry.stat().st_mtime) > STALE_SECONDS:
                entry.unlink()
        except OSError:
            continue


def _tail_lines(transcript_path: str) -> deque:
    buffer: deque = deque(maxlen=TAIL_LINES)
    with open(transcript_path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            buffer.append(line)
    return buffer


def _parse_records(lines: deque) -> list[dict[str, Any]]:
    records = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _content_blocks(record: dict[str, Any]) -> list[Any] | None:
    message = record.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    return content if isinstance(content, list) else None


def _is_turn_start(record: dict[str, Any]) -> bool:
    if record.get("type") != "user":
        return False
    blocks = _content_blocks(record)
    if blocks is None:
        return True
    return not any(isinstance(block, dict) and block.get("type") == "tool_result" for block in blocks)


def _find_turn_start(records: list[dict[str, Any]]) -> int:
    for index in range(len(records) - 1, -1, -1):
        if _is_turn_start(records[index]):
            return index + 1
    return 0


def _tool_use_names(records: list[dict[str, Any]]) -> list[str]:
    names = []
    for record in records:
        blocks = _content_blocks(record)
        if not blocks:
            continue
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                name = block.get("name")
                if name:
                    names.append(name)
    return names


def _is_delegation(name: str) -> bool:
    return name in DELEGATION_NAMES or name.startswith(DELEGATION_PREFIX)


def _render_tally(names: list[str]) -> str:
    counts = Counter(names)
    delegate_total = sum(count for name, count in counts.items() if _is_delegation(name))
    direct = sorted(
        ((name, count) for name, count in counts.items() if not _is_delegation(name)),
        key=lambda pair: (-pair[1], pair[0]),
    )
    parts = [f"{name}×{count}" for name, count in direct]
    parts.append(f"Delegate×{delegate_total}")
    return " ".join(parts)


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    sid = _sanitize_session_id(str(payload.get("session_id") or ""))
    if not sid:
        return

    state_dir = _state_dir()
    _reap_stale(state_dir)

    transcript_path = payload.get("transcript_path") or ""
    if not transcript_path:
        return

    try:
        lines = _tail_lines(transcript_path)
    except OSError:
        return

    all_records = _parse_records(lines)
    records = [record for record in all_records if not record.get("isSidechain")]
    if not records:
        return

    start = _find_turn_start(records)
    names = _tool_use_names(records[start:])
    tally = _render_tally(names)
    (state_dir / f"head-tally.{sid}").write_text(tally + "\n", encoding="utf-8")


if __name__ == "__main__":
    # Hook contract: never raise, always exit 0, whatever went wrong.
    with contextlib.suppress(BaseException):
        main()
    raise SystemExit(0)
