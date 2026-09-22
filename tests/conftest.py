"""Shared pytest fixtures: a fake HOME forest for discover/*, and a fake `claude` binary for
heads/*.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from cc_interproject import paths

_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
_FOREST_SOURCE = _FIXTURES_DIR / "forest"
_CLAUDE_FAKE_DIR = _FIXTURES_DIR / "claude_fake"


@pytest.fixture
def forest_home(tmp_path: Path) -> Path:
    """Copy `fixtures/forest` into a fresh temporary HOME.

    `alpha`'s absolute path is different once copied, so the checked-in session directory name
    under `dot-claude/projects/` no longer matches it (see
    `fixtures/forest/dot-claude/projects/README.md`). This re-encodes it with the same
    forward-encoding logic the installer uses and renames the directory to match.
    """
    home = tmp_path / "home"
    shutil.copytree(_FOREST_SOURCE, home)
    projects_dir = home / "dot-claude" / "projects"
    stale_session_dirs = [entry for entry in projects_dir.iterdir() if entry.is_dir()]
    real_name = paths.encode_project_dir(home / "alpha")[0]
    for stale_dir in stale_session_dirs:
        stale_dir.rename(projects_dir / real_name)
    return home


@pytest.fixture
def fake_claude_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Put `fixtures/claude_fake` first on `PATH` so `shutil.which("claude")` finds the fake
    binary, and default `KIT_FAKE_MODE` to `"ok"`.
    """
    monkeypatch.setenv("PATH", f"{_CLAUDE_FAKE_DIR}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("KIT_FAKE_MODE", "ok")
