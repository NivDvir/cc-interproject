"""Filesystem locations under `~/.claude` (or a `--root`'s `dot-claude` stand-in in tests),
per-OS directory skip lists for the forest walk, and `~/.claude/projects` name encoding.
"""

from __future__ import annotations

import os
import pkgutil
import re
import shutil
import sys
from pathlib import Path, PurePath

KIT_NAME = "cc-interproject"
MANIFEST_NAME = "interproject.manifest.json"
BACKUPS_SUBDIR = "interproject-backups"

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
    session transcripts) when it scans `$HOME`; the kit's own fixtures use `dot-claude` as a
    stand-in for exactly this reason.
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


def home_dir() -> Path:
    """The user's home directory: `Path.home()`, except on Windows, where an explicit `HOME` env
    var wins when set.

    `Path.home()` on Windows reads `USERPROFILE` and ignores `HOME` entirely, so a caller
    sandboxing a run by setting only `HOME` (this repo's own end-to-end tests included) would
    otherwise land outside the sandbox there. Off Windows, `Path.home()` already honours `HOME`
    itself, so re-checking it here would only get in the way of a test that mocks `Path.home()`
    directly.
    """
    if sys.platform.startswith("win"):
        override = os.environ.get("HOME")
        if override:
            return Path(override)
    return Path.home()


def manifest_path(claude_dir: Path) -> Path:
    return claude_dir / MANIFEST_NAME


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


def is_windows_shim(claude_bin: str) -> bool:
    """True when `claude_bin` resolves to a `.cmd`/`.bat` file — the normal shape of a real,
    npm-installed `claude` on Windows. `CreateProcess` cannot start such a file directly (no PE
    header): only `cmd.exe` knows how to run it. Always false off Windows.
    """
    if not sys.platform.startswith("win"):
        return False
    resolved = shutil.which(claude_bin) or claude_bin
    return resolved.lower().endswith((".cmd", ".bat"))


def windows_shim_argv(command: list[str]) -> list[str]:
    """Rewrite `command` so a `.cmd`/`.bat` shim runs through the command interpreter instead of
    being handed to `CreateProcess` directly, which fails with `OSError` (`WinError 193`). A
    no-op everywhere except Windows, and even there a no-op unless `command[0]` resolves to a
    batch file. See `heads/ARCHITECTURE.md` for why this wraps the resolved binary in
    `cmd.exe /d /c` rather than parsing the shim to find the real interpreter underneath it.
    """
    if not is_windows_shim(command[0]):
        return command
    resolved = shutil.which(command[0]) or command[0]
    comspec = os.environ.get("COMSPEC", "cmd.exe")
    return [comspec, "/d", "/c", resolved, *command[1:]]
