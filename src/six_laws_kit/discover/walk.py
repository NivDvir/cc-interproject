"""Walk a home directory for Claude Code projects: any directory holding its own `CLAUDE.md`,
skipping vendored and OS housekeeping directories and never following a symlink.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

_PROGRESS_INTERVAL = 200
_SKIPPED_ROOT_DEPTH_CAP = 2
_CLAUDE_MD = "CLAUDE.md"


def find_projects(
    root: Path,
    skip: set[str],
    on_progress: Callable[[int], None],
    max_depth: int = 6,
    max_dirs: int = 200_000,
) -> tuple[list[Path], list[Path]]:
    """Return `(claude_md_paths, skipped_roots)` found scanning below `root`.

    `skip` names are never entered, at any depth — including inside a directory that itself
    holds a `CLAUDE.md`, so a discovered project's own vendored or virtual-env directories are still
    skipped. `skipped_roots` only records the ones actually encountered at depth <= 2, so the
    caller can name a few without flooding the UI with every vendored directory buried deep in a
    tree. A symlink (or, on Windows, a reparse point) is never descended into, which is also what
    keeps a symlink loop from hanging the walk. `on_progress` fires every 200 directories and
    once more, unconditionally, when the walk finishes, so the final call always carries the
    exact total even when it is not a multiple of 200 (or is 0).
    """
    claude_mds: list[Path] = []
    skipped_roots: list[Path] = []
    dirs_seen = 0

    def visit(directory: Path, depth: int) -> None:
        nonlocal dirs_seen
        if dirs_seen >= max_dirs:
            return
        dirs_seen += 1
        if dirs_seen % _PROGRESS_INTERVAL == 0:
            on_progress(dirs_seen)
        try:
            entries = list(os.scandir(directory))
        except OSError:
            return
        for entry in entries:
            if entry.name == _CLAUDE_MD and entry.is_file(follow_symlinks=False):
                claude_mds.append(Path(entry.path))
        if depth < max_depth:
            _visit_subdirs(entries, depth, skip, skipped_roots, visit)

    def _visit_subdirs(
        entries: list[os.DirEntry],
        depth: int,
        skip: set[str],
        skipped_roots: list[Path],
        visit_fn: Callable[[Path, int], None],
    ) -> None:
        for entry in entries:
            if not entry.is_dir(follow_symlinks=False):
                continue
            if entry.name in skip:
                if depth + 1 <= _SKIPPED_ROOT_DEPTH_CAP:
                    skipped_roots.append(Path(entry.path))
                continue
            visit_fn(Path(entry.path), depth + 1)

    visit(root, 0)
    on_progress(dirs_seen)
    return claude_mds, skipped_roots
