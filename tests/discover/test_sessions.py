"""Tests for discover/sessions.py: session lookup by encoded project path and last-session
dating.
"""

from __future__ import annotations

from datetime import datetime, timezone

from six_laws_kit import paths
from six_laws_kit.discover import forest, sessions, walk


def test_sessions_annotates_alpha_and_leaves_beta_bare(forest_home):
    claude_mds, _ = walk.find_projects(forest_home, paths.skip_names(), on_progress=lambda _n: None)
    trees = forest.build(claude_mds)
    claude_dir = forest_home / "dot-claude"

    sessions.annotate(trees, claude_dir)

    by_path = {tree.path: tree for tree in trees}
    alpha = by_path[forest_home / "alpha"]
    beta = by_path[forest_home / "beta"]

    assert alpha.has_session is True
    session_dir = claude_dir / "projects" / paths.encode_project_dir(forest_home / "alpha")[0]
    newest_mtime = max(entry.stat().st_mtime for entry in session_dir.glob("*.jsonl"))
    expected = datetime.fromtimestamp(newest_mtime, tz=timezone.utc).date().isoformat()
    assert alpha.last_session == expected

    assert beta.has_session is False
    assert beta.last_session is None
