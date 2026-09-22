"""Subprocess tests for `six_laws_kit.hooks.packet_reminder` (the UserPromptSubmit hook). Run the
file directly, as it will be run in the field, with a temp HOME. Each test copies the script into
its own scratch directory so a real `PACKET_REMINDER.md` sitting next to the source file (copied
there only at install time) never leaks into a test that expects it absent. Does not depend on
`tests/conftest.py`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "src" / "six_laws_kit" / "hooks" / "packet_reminder.py"


def _isolated_script(scratch: Path) -> Path:
    """Copy the hook alone into `scratch`, with no adjacent PACKET_REMINDER.md."""
    copy_path = scratch / "packet_reminder.py"
    shutil.copy(SCRIPT, copy_path)
    return copy_path


def _run(script: Path, payload: dict, home: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        check=False,
    )


def test_tally_file_is_surfaced_deleted_and_turn_reset(tmp_path: Path) -> None:
    home = tmp_path / "home"
    scratch = tmp_path / "scratch"
    home.mkdir()
    scratch.mkdir()
    script = _isolated_script(scratch)

    state_dir = home / ".claude" / "six-laws-state"
    state_dir.mkdir(parents=True)
    tally_file = state_dir / "head-tally.sid-a"
    tally_file.write_text("Read×2 Delegate×0\n", encoding="utf-8")
    delegated_file = state_dir / "turn-delegated.sid-a"
    delegated_file.write_text("", encoding="utf-8")

    result = _run(script, {"session_id": "sid-a", "cwd": "/x", "prompt": "hi"}, home)

    assert result.returncode == 0
    output = json.loads(result.stdout)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "LAST TURN (your own tool calls): Read×2 Delegate×0" in context

    assert not tally_file.exists()
    assert not delegated_file.exists()
    loads_file = state_dir / "turn-loads.sid-a"
    assert loads_file.read_text(encoding="utf-8").strip() == "0 6"


def test_no_tally_and_no_reminder_prints_nothing(tmp_path: Path) -> None:
    home = tmp_path / "home"
    scratch = tmp_path / "scratch"
    home.mkdir()
    scratch.mkdir()
    script = _isolated_script(scratch)

    result = _run(script, {"session_id": "sid-b", "cwd": "/x", "prompt": "hi"}, home)

    assert result.returncode == 0
    assert result.stdout == ""
    loads_file = home / ".claude" / "six-laws-state" / "turn-loads.sid-b"
    assert loads_file.read_text(encoding="utf-8").strip() == "0 6"


def test_reminder_file_is_included_when_present(tmp_path: Path) -> None:
    home = tmp_path / "home"
    scratch = tmp_path / "scratch"
    home.mkdir()
    scratch.mkdir()
    script = _isolated_script(scratch)
    (scratch / "PACKET_REMINDER.md").write_text("Plan the task first.\n", encoding="utf-8")

    result = _run(script, {"session_id": "sid-c", "cwd": "/x", "prompt": "hi"}, home)

    assert result.returncode == 0
    output = json.loads(result.stdout)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "Plan the task first." in context
    assert "LAST TURN" not in context


def test_missing_session_id_does_nothing(tmp_path: Path) -> None:
    home = tmp_path / "home"
    scratch = tmp_path / "scratch"
    home.mkdir()
    scratch.mkdir()
    script = _isolated_script(scratch)

    result = _run(script, {"cwd": "/x", "prompt": "hi"}, home)

    assert result.returncode == 0
    assert result.stdout == ""
    assert not (home / ".claude").exists()
