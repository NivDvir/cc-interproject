"""Subprocess tests for `six_laws_kit.hooks.load_cap` (the PreToolUse hook). Run the file
directly, as it will be run in the field, with a temp HOME. Does not depend on `tests/conftest.py`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "src" / "six_laws_kit" / "hooks" / "load_cap.py"


def _run(payload: dict, home: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["HOME"] = str(home)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
        check=False,
    )


def _state_dir(home: Path) -> Path:
    return home / ".claude" / "six-laws-state"


def test_no_loads_file_allows_silently_and_writes_nothing(tmp_path: Path) -> None:
    result = _run({"session_id": "sid-worker", "tool_name": "Read", "tool_input": {}}, tmp_path)

    assert result.returncode == 0
    assert result.stdout == ""
    assert not (_state_dir(tmp_path) / "turn-loads.sid-worker").exists()


def test_six_allowed_seventh_denied_then_threshold_raised(tmp_path: Path) -> None:
    state_dir = _state_dir(tmp_path)
    state_dir.mkdir(parents=True)
    loads_file = state_dir / "turn-loads.sid-cap"
    loads_file.write_text("0 6\n", encoding="utf-8")

    for expected_count in range(1, 7):
        result = _run({"session_id": "sid-cap", "tool_name": "Read", "tool_input": {}}, tmp_path)
        assert result.returncode == 0
        assert result.stdout == "", f"call {expected_count} should be a silent allow"
        assert loads_file.read_text(encoding="utf-8").strip() == f"{expected_count} 6"

    seventh = _run({"session_id": "sid-cap", "tool_name": "Read", "tool_input": {}}, tmp_path)
    assert seventh.returncode == 0
    payload = json.loads(seventh.stdout)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert loads_file.read_text(encoding="utf-8").strip() == "7 12"

    eighth = _run({"session_id": "sid-cap", "tool_name": "Read", "tool_input": {}}, tmp_path)
    assert eighth.returncode == 0
    assert eighth.stdout == ""
    assert loads_file.read_text(encoding="utf-8").strip() == "8 12"


def test_delegation_tool_switches_cap_off(tmp_path: Path) -> None:
    state_dir = _state_dir(tmp_path)
    state_dir.mkdir(parents=True)
    loads_file = state_dir / "turn-loads.sid-deleg"
    loads_file.write_text("6 6\n", encoding="utf-8")

    delegate_result = _run({"session_id": "sid-deleg", "tool_name": "Agent", "tool_input": {}}, tmp_path)
    assert delegate_result.returncode == 0
    assert delegate_result.stdout == ""
    assert (state_dir / "turn-delegated.sid-deleg").exists()
    assert loads_file.read_text(encoding="utf-8").strip() == "6 6"

    after_delegation = _run({"session_id": "sid-deleg", "tool_name": "Read", "tool_input": {}}, tmp_path)
    assert after_delegation.returncode == 0
    assert after_delegation.stdout == ""
    assert loads_file.read_text(encoding="utf-8").strip() == "6 6"


def test_corrupt_state_file_fails_open_to_silent_allow(tmp_path: Path) -> None:
    state_dir = _state_dir(tmp_path)
    state_dir.mkdir(parents=True)
    loads_file = state_dir / "turn-loads.sid-corrupt"
    loads_file.write_text("not-a-number garbage\n", encoding="utf-8")

    result = _run({"session_id": "sid-corrupt", "tool_name": "Read", "tool_input": {}}, tmp_path)

    assert result.returncode == 0
    assert result.stdout == ""
    assert loads_file.read_text(encoding="utf-8").strip() == "1 6"


def test_uncounted_tool_is_allowed_without_incrementing(tmp_path: Path) -> None:
    state_dir = _state_dir(tmp_path)
    state_dir.mkdir(parents=True)
    loads_file = state_dir / "turn-loads.sid-uncounted"
    loads_file.write_text("2 6\n", encoding="utf-8")

    result = _run({"session_id": "sid-uncounted", "tool_name": "Write", "tool_input": {}}, tmp_path)

    assert result.returncode == 0
    assert result.stdout == ""
    assert loads_file.read_text(encoding="utf-8").strip() == "2 6"
