"""UserPromptSubmit hook: reset the per-turn load-cap counter and remind the head of the
SELF/DELEGATE packet workflow. Reads one JSON object from stdin (`session_id`, `cwd`, `prompt`).
Consumes the tally the Stop hook (`labor_tally.py`) left for this session, resets
`turn-loads.<sid>` so `load_cap.py` starts counting fresh, and prints an `additionalContext` string
that opens with last turn's tally (if any) followed by the public packet-reminder text from
`PACKET_REMINDER.md` (if present next to this file). This program is standalone: it imports
nothing from the `six_laws_kit` package, since it is copied alone to `~/.claude/hooks/six-laws/`.

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
RESET_LOADS_LINE = "0 6"


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


def _read_and_delete_tally(state_dir: Path, sid: str) -> str:
    tally_file = state_dir / f"head-tally.{sid}"
    tally = ""
    try:
        tally = tally_file.read_text(encoding="utf-8").strip()
    except OSError:
        tally = ""
    with contextlib.suppress(FileNotFoundError):
        tally_file.unlink()
    return tally


def _reset_turn_files(state_dir: Path, sid: str) -> None:
    (state_dir / f"turn-loads.{sid}").write_text(RESET_LOADS_LINE + "\n", encoding="utf-8")
    with contextlib.suppress(FileNotFoundError):
        (state_dir / f"turn-delegated.{sid}").unlink()


def _reminder_text() -> str:
    reminder_path = Path(__file__).resolve().parent / "PACKET_REMINDER.md"
    try:
        return reminder_path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _build_context(tally: str, reminder: str) -> str:
    lines = []
    if tally:
        lines.append(f"LAST TURN (your own tool calls): {tally}")
    if reminder:
        lines.append(reminder)
    return "\n".join(lines)


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")
    sid = _sanitize_session_id(str(payload.get("session_id") or ""))
    if not sid:
        return

    state_dir = _state_dir()
    tally = _read_and_delete_tally(state_dir, sid)
    _reset_turn_files(state_dir, sid)

    context = _build_context(tally, _reminder_text())
    if not context:
        return

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": context,
                }
            }
        )
    )


if __name__ == "__main__":
    # Hook contract: never raise, always exit 0, whatever went wrong.
    with contextlib.suppress(BaseException):
        main()
    raise SystemExit(0)
