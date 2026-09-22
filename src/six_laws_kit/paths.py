"""Filesystem locations under `~/.claude` (or a `--root`'s `dot-claude` stand-in in tests),
per-OS directory skip lists for the forest walk, `~/.claude/projects` name encoding, and the two
helpers that build a hook's registered command.
"""

from __future__ import annotations

import pkgutil
import re
import shutil
import sys
from pathlib import Path, PurePath

KIT_NAME = "six-laws-kit"
MANIFEST_NAME = "six-laws.manifest.json"
HOOKS_SUBDIR = "hooks/six-laws"
STATE_SUBDIR = "six-laws-state"
BACKUPS_SUBDIR = "six-laws-backups"

_BASE_SKIP_NAMES = {
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
}
_WINDOWS_EXTRA_SKIP_NAMES = {"AppData", "OneDrive", "$Recycle.Bin"}

_ENCODE_DROP_UNDERSCORE = re.compile(r"[^A-Za-z0-9-]")
_ENCODE_KEEP_UNDERSCORE = re.compile(r"[^A-Za-z0-9_-]")


def skip_names() -> set[str]:
    """Return the directory names the forest walk never enters, for the current OS.

    These are exact directory names, matched by name only — never a glob or pattern. `.claude`
    is included so the walk never descends into Claude Code's own state (worktree checkouts,
    hooks, session transcripts) when it scans `$HOME`; the kit's own fixtures use `dot-claude` as
    a stand-in for exactly this reason.
    """
    names = set(_BASE_SKIP_NAMES)
    if sys.platform.startswith("win"):
        names |= _WINDOWS_EXTRA_SKIP_NAMES
    return names


def read_package_resource(package: str, resource: str) -> str:
    """Read one text file this package ships, addressed by dotted package name and a
    forward-slash relative path (e.g. `"assets/index.html"`), from the source tree or from
    inside the zipapp bundle alike.

    Goes through `pkgutil.get_data` rather than `importlib.resources.files(...).joinpath(...)`:
    on Windows, `importlib.resources`'s zipimport-backed reader can join the package's own
    zip-internal prefix to the resource name with `os.sep` instead of `/`, producing a mixed
    separator that is not a real archive member (seen on Python 3.9). `pkgutil.get_data`
    normalizes separators itself and has no such bug.
    """
    data = pkgutil.get_data(package, resource)
    if data is None:
        raise FileNotFoundError(resource)
    return data.decode("utf-8")


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
