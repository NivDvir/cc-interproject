"""Annotate each Tree with whether `<claude_dir>/projects` holds a session transcript for it,
and the date of the most recent one.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from six_laws_kit.paths import encode_project_dir
from six_laws_kit.run_state import Tree


def annotate(trees: list[Tree], claude_dir: Path) -> None:
    """Set `has_session` / `last_session` on every tree and subtree, in place."""
    projects_dir = claude_dir / "projects"
    for tree in trees:
        _annotate_one(tree, projects_dir)


def _annotate_one(tree: Tree, projects_dir: Path) -> None:
    session_dir = _find_session_dir(tree.path, projects_dir)
    tree.has_session = session_dir is not None
    tree.last_session = _latest_jsonl_date(session_dir) if session_dir else None
    for subtree in tree.subtrees:
        _annotate_one(subtree, projects_dir)


def _find_session_dir(path: Path, projects_dir: Path) -> Path | None:
    for name in encode_project_dir(path):
        candidate = projects_dir / name
        if candidate.is_dir():
            return candidate
    return None


def _latest_jsonl_date(session_dir: Path) -> str | None:
    newest_mtime: float | None = None
    for entry in session_dir.glob("*.jsonl"):
        mtime = entry.stat().st_mtime
        if newest_mtime is None or mtime > newest_mtime:
            newest_mtime = mtime
    if newest_mtime is None:
        return None
    return datetime.fromtimestamp(newest_mtime, tz=timezone.utc).date().isoformat()
