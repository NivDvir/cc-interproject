"""Tests for cc_interproject.cli: argument parsing, preflight gating, and the exit codes documented
in cli.main's own docstring.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from cc_interproject import VERSION, cli


def _hash_tree(root: Path) -> dict:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _scripted_input(monkeypatch, lines: list[str]) -> None:
    remaining = list(lines)

    def fake_input(prompt: str = "") -> str:
        if not remaining:
            raise EOFError
        return remaining.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)


def test_version_flag_prints_name_and_version(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"cc-interproject {VERSION}"


def test_conflicting_mode_flags_exit_2():
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["--dry-run", "--status"])
    assert excinfo.value.code == 2


def test_missing_claude_exits_3(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))  # an empty directory: no `claude` binary on PATH
    code = cli.main(["--dry-run", "--no-browser", "--root", str(tmp_path)])
    assert code == 3


def test_status_with_no_manifest_prints_not_installed(forest_home, capsys):
    code = cli.main(["--status", "--root", str(forest_home)])
    assert code == 0
    assert "not installed" in capsys.readouterr().out


def test_dry_run_writes_nothing(forest_home, fake_claude_on_path, monkeypatch):
    monkeypatch.setenv("KIT_SKIP_AUTH", "1")
    _scripted_input(monkeypatch, ["all"])
    before = _hash_tree(forest_home)

    code = cli.main(["--dry-run", "--no-browser", "--root", str(forest_home)])

    assert code == 0
    assert _hash_tree(forest_home) == before
