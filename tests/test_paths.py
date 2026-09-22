"""Tests for paths.py: skip lists, directory helpers, project-dir encoding, and hook command
rendering.
"""

from __future__ import annotations

import sys
from pathlib import Path, PureWindowsPath

from six_laws_kit import paths


def test_skip_names_includes_common_vendored_dirs():
    names = paths.skip_names()
    assert {"node_modules", ".venv", ".git", ".Trash"} <= names


def test_skip_names_adds_windows_extras_only_on_windows():
    names = paths.skip_names()
    if sys.platform.startswith("win"):
        assert "AppData" in names
    else:
        assert "AppData" not in names


def test_manifest_hooks_state_backups_paths(tmp_path):
    claude_dir = tmp_path / ".claude"
    assert paths.manifest_path(claude_dir) == claude_dir / "six-laws.manifest.json"
    assert paths.hooks_dir(claude_dir) == claude_dir / "hooks" / "six-laws"
    assert paths.state_dir(claude_dir) == claude_dir / "six-laws-state"
    assert paths.backups_dir(claude_dir, "2026-09-22") == claude_dir / "six-laws-backups" / "2026-09-22"


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


def test_hook_command_quotes_the_script_path():
    command = paths.hook_command(["python3"], Path("/opt/six laws/hook.py"))
    assert command == 'python3 "/opt/six laws/hook.py"'


def test_hook_command_joins_multi_part_interpreter():
    command = paths.hook_command(["py", "-3"], Path("/opt/hook.py"))
    assert command == 'py -3 "/opt/hook.py"'
