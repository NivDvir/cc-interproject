"""PreToolUse hook: after too many direct context-loading tool calls in one head turn with zero
delegation, deny the next one so the head must dispatch a packet (or justify the step as SELF).
Reads one JSON object from stdin (`session_id`, `tool_name`, `tool_input`). This program is
standalone: it imports nothing from the `six_laws_kit` package, since it is copied alone to
`~/.claude/hooks/six-laws/`.

Worker discriminator: `packet_reminder.py` (UserPromptSubmit) writes `turn-loads.<sid>` at the
start of every HEAD turn; UserPromptSubmit never fires for sub-agent workers, so that file never
exists for them. No file means allow silently and do nothing further: workers are never capped.

Fail-open contract: every unexpected condition (missing field, unreadable or corrupt state file,
anything at all) allows. Deny happens on exactly one explicit path. Allow is always silent (no
JSON) so it never bypasses the user's own permission rules; only deny prints JSON. A deny raises
the stored threshold so the head can always proceed after acknowledging it.

Exit code: always 0. Never raises.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
from pathlib import Path

SID_MAX_LEN = 128
STATE_DIRNAME = "six-laws-state"
THRESHOLD_STEP = 6
DEFAULT_THRESHOLD = 6
DELEGATION_NAMES = {"Agent", "Task", "SendMessage"}
DELEGATION_PREFIX = "mcp__dispatch__start"
COUNTED_TOOLS = {"Read", "Grep", "Glob", "Bash", "WebFetch"}


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


def _is_delegation(name: str) -> bool:
    return name in DELEGATION_NAMES or name.startswith(DELEGATION_PREFIX)


def _parse_counter(raw: str) -> tuple:
    parts = raw.split()
    try:
        count = int(parts[0])
    except (IndexError, ValueError):
        count = 0
    try:
        threshold = int(parts[1])
    except (IndexError, ValueError):
        threshold = DEFAULT_THRESHOLD
    if threshold <= 0:
        threshold = DEFAULT_THRESHOLD
    return count, threshold


def _deny_reason(count: int) -> str:
    return (
        f"{count} direct context loads this turn with zero delegation; write a packet and dispatch a worker."
    )


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    sid = _sanitize_session_id(str(payload.get("session_id") or ""))
    if not sid:
        return

    state_dir = _state_dir()
    loads_file = state_dir / f"turn-loads.{sid}"
    if not loads_file.exists():
        return

    tool_name = str(payload.get("tool_name") or "")
    if not tool_name:
        return

    delegated_file = state_dir / f"turn-delegated.{sid}"
    if _is_delegation(tool_name):
        delegated_file.touch()
        return

    if tool_name not in COUNTED_TOOLS:
        return

    if delegated_file.exists():
        return

    try:
        raw = loads_file.read_text(encoding="utf-8")
    except OSError:
        return

    count, threshold = _parse_counter(raw)
    count += 1

    if count > threshold:
        new_threshold = threshold + THRESHOLD_STEP
        loads_file.write_text(f"{count} {new_threshold}\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": _deny_reason(count),
                    }
                }
            )
        )
        return

    loads_file.write_text(f"{count} {threshold}\n", encoding="utf-8")


if __name__ == "__main__":
    # Hook contract: never raise, always exit 0, whatever went wrong.
    with contextlib.suppress(BaseException):
        main()
    raise SystemExit(0)
