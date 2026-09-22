"""Subprocess tests for `six_laws_kit.hooks.labor_tally` (the Stop hook). Run the file directly, as
it will be run in the field — never imported — with a temp HOME so state never touches the real
`~/.claude/six-laws-state/`. Does not depend on `tests/conftest.py`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "src" / "six_laws_kit" / "hooks" / "labor_tally.py"
FIXTURES = ROOT / "fixtures" / "transcripts"


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


def _tally_path(home: Path, sid: str) -> Path:
    return home / ".claude" / "six-laws-state" / f"head-tally.{sid}"


def test_head_turn_tallies_non_sidechain_tool_calls(tmp_path: Path) -> None:
    result = _run(
        {"session_id": "sid-head", "transcript_path": str(FIXTURES / "head_turn.jsonl")},
        tmp_path,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    tally_file = _tally_path(tmp_path, "sid-head")
    assert tally_file.read_text(encoding="utf-8").strip() == "Read×7 Bash×3 Delegate×1"


def test_worker_turn_all_sidechain_writes_no_tally(tmp_path: Path) -> None:
    result = _run(
        {"session_id": "sid-worker", "transcript_path": str(FIXTURES / "worker_turn.jsonl")},
        tmp_path,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert not _tally_path(tmp_path, "sid-worker").exists()


def test_malformed_lines_are_skipped_without_crashing(tmp_path: Path) -> None:
    result = _run(
        {"session_id": "sid-malformed", "transcript_path": str(FIXTURES / "malformed.jsonl")},
        tmp_path,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_missing_session_id_does_nothing(tmp_path: Path) -> None:
    result = _run({"transcript_path": str(FIXTURES / "head_turn.jsonl")}, tmp_path)
    assert result.returncode == 0
    assert result.stdout == ""
    assert not (tmp_path / ".claude").exists()


def test_missing_transcript_path_writes_no_tally(tmp_path: Path) -> None:
    result = _run({"session_id": "sid-no-transcript"}, tmp_path)
    assert result.returncode == 0
    assert not _tally_path(tmp_path, "sid-no-transcript").exists()


def test_reaps_state_files_older_than_one_day(tmp_path: Path) -> None:
    state_dir = tmp_path / ".claude" / "six-laws-state"
    state_dir.mkdir(parents=True)
    stale = state_dir / "head-tally.stale-session"
    stale.write_text("Read×1 Delegate×0\n", encoding="utf-8")
    two_days_ago = time.time() - (2 * 24 * 60 * 60)
    os.utime(stale, (two_days_ago, two_days_ago))

    result = _run({"session_id": "sid-reap", "transcript_path": ""}, tmp_path)

    assert result.returncode == 0
    assert not stale.exists()
