from __future__ import annotations

import hashlib
from pathlib import Path

from cc_interproject.manifest import status
from cc_interproject.run_state import Run


def test_report_when_nothing_is_installed(tmp_path: Path):
    text = status.report(None, tmp_path)
    assert "not installed" in text
    assert str(tmp_path) in text


def test_report_lists_entries_and_head_counts(tmp_path: Path):
    # write_bytes, not write_text: text mode's universal-newline translation would turn "\n" into
    # "\r\n" on Windows, so the file's real bytes would no longer match the sha256 below.
    target = tmp_path / "INTERPROJECT_LAWS.md"
    target.write_bytes(b"law\n")
    sha = hashlib.sha256(b"law\n").hexdigest()
    manifest = {
        "kit_version": "0.1.0",
        "installed_at": "2026-01-01T00:00:00Z",
        "entries": [{"kind": "created_file", "path": str(target), "sha256_after": sha}],
        "heads": [
            {"path": "/home/alpha", "written_by": "self", "status": "ok"},
            {"path": "/home/beta", "written_by": "installer", "status": "fallback"},
        ],
    }
    text = status.report(manifest, tmp_path)
    assert "0.1.0" in text
    assert "(unchanged)" in text
    assert "self: 1  installer: 1" in text


def test_report_flags_a_modified_entry(tmp_path: Path):
    target = tmp_path / "INTERPROJECT_LAWS.md"
    target.write_text("law\n", encoding="utf-8")
    manifest = {
        "entries": [{"kind": "created_file", "path": str(target), "sha256_after": "deadbeef"}],
        "heads": [],
    }
    assert "(modified)" in status.report(manifest, tmp_path)


def test_report_flags_a_missing_entry(tmp_path: Path):
    manifest = {
        "entries": [{"kind": "created_file", "path": str(tmp_path / "gone.md"), "sha256_after": "x"}],
        "heads": [],
    }
    assert "(missing)" in status.report(manifest, tmp_path)


def test_run_prints_the_report_and_returns_zero(tmp_path: Path, capsys):
    run_obj = Run(
        mode="status", home=tmp_path, claude_dir=tmp_path / "dot-claude", root=tmp_path, no_browser=True
    )
    assert status.run(run_obj) == 0
    assert "not installed" in capsys.readouterr().out
