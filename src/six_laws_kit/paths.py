"""Filesystem locations under `~/.claude` (or a `--root`'s `dot-claude` stand-in in tests),
per-OS directory skip lists for the forest walk, `~/.claude/projects` name encoding, and the two
helpers that build a hook's registered command.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path, PurePath

KIT_NAME = "six-laws-kit"
MANIFEST_NAME = "six-laws.manifest.json"
HOOKS_SUBDIR = "hooks/six-laws"
STATE_SUBDIR = "six-laws-state"
BACKUPS_SUBDIR = "six-laws-backups"

_POSIX_SKIP_NAMES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".cache",
    ".npm",
    ".cargo",
    "Library",
    ".Trash",
    "Pictures",
    "Movies",
    "Music",
}
_WINDOWS_EXTRA_SKIP_NAMES = {"AppData", "OneDrive", "$Recycle.Bin"}

_ENCODE_DROP_UNDERSCORE = re.compile(r"[^A-Za-z0-9-]")
_ENCODE_KEEP_UNDERSCORE = re.compile(r"[^A-Za-z0-9_-]")


def skip_names() -> set[str]:
    """Return the directory names the forest walk never enters, for the current OS."""
    names = set(_POSIX_SKIP_NAMES)
    if sys.platform.startswith("win"):
        names |= _WINDOWS_EXTRA_SKIP_NAMES
    return names


def manifest_path(claude_dir: Path) -> Path:
    return claude_dir / MANIFEST_NAME


def hooks_dir(claude_dir: Path) -> Path:
    return claude_dir / HOOKS_SUBDIR


def state_dir(claude_dir: Path) -> Path:
    return claude_dir / STATE_SUBDIR


def backups_dir(claude_dir: Path, stamp: str) -> Path:
    return claude_dir / BACKUPS_SUBDIR / stamp


def encode_project_dir(path: Path) -> list[str]:
    """Return the candidate `~/.claude/projects` directory names for `path`, forward-encoded.

    Two candidates come back: the strict encoding, where every character outside
    `[A-Za-z0-9-]` (including underscore) becomes `-`, and a variant that additionally keeps
    underscores. Callers looking a project up under `~/.claude/projects` try both, since which
    one a given Claude Code version wrote is not guaranteed. Accepts any `PurePath` (a
    `PureWindowsPath` included), since encoding never touches the filesystem.
    """
    posix = PurePath(path).as_posix()
    return [
        _ENCODE_DROP_UNDERSCORE.sub("-", posix),
        _ENCODE_KEEP_UNDERSCORE.sub("-", posix),
    ]


def hook_interpreter() -> list[str]:
    """Return the interpreter argv for running a hook script: the `py` launcher on Windows when
    it is present, else `python3`.
    """
    if sys.platform.startswith("win") and shutil.which("py"):
        return ["py", "-3"]
    return ["python3"]


def hook_command(interpreter: list[str], script: Path) -> str:
    """Render the `settings.json` hook command string for `script`, quoted as a POSIX path."""
    return " ".join([*interpreter, f'"{script.as_posix()}"'])
