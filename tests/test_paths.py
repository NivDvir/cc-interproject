"""Tests for paths.py: skip lists, directory helpers, and project-dir encoding."""

from __future__ import annotations

import sys
from pathlib import Path, PureWindowsPath

from cc_interproject import paths


def test_skip_names_includes_common_vendored_dirs():
    names = paths.skip_names()
    assert {"node_modules", ".venv", ".git", ".Trash"} <= names


def test_skip_names_includes_claude_and_build_tool_dirs_on_every_os():
    names = paths.skip_names()
    assert {
        ".claude",
        ".build",
        "worktrees",
        "checkouts",
        "dist",
        "build",
        "target",
        ".tox",
        ".mypy_cache",
        ".ruff_cache",
        ".pytest_cache",
        "site-packages",
    } <= names


def test_skip_names_adds_windows_extras_only_on_windows():
    names = paths.skip_names()
    if sys.platform.startswith("win"):
        assert "AppData" in names
    else:
        assert "AppData" not in names


def test_manifest_and_backups_paths(tmp_path):
    claude_dir = tmp_path / ".claude"
    assert paths.manifest_path(claude_dir) == claude_dir / "interproject.manifest.json"
    assert paths.backups_dir(claude_dir, "2026-09-22") == claude_dir / "interproject-backups" / "2026-09-22"


def test_encode_project_dir_posix_path():
    encodings = paths.encode_project_dir(Path("/Users/guydvir/opportunity-radar"))
    assert "-Users-guydvir-opportunity-radar" in encodings


def test_encode_project_dir_keeps_underscore_variant():
    encodings = paths.encode_project_dir(Path("/Users/guydvir/my_proj.sub"))
    assert "-Users-guydvir-my-proj-sub" in encodings
    assert "-Users-guydvir-my_proj-sub" in encodings


def test_encode_project_dir_windows_style_path():
    encodings = paths.encode_project_dir(PureWindowsPath("C:\\Users\\x\\proj"))
    assert any(name.endswith("Users-x-proj") for name in encodings)
