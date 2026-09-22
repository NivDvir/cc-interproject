"""Tests for discover/forest.py: nesting subtrees under their nearest ancestor project, naming
from the CLAUDE.md heading, and selection inheritance.
"""

from __future__ import annotations

from pathlib import Path

from six_laws_kit import paths
from six_laws_kit.discover import forest, walk
from six_laws_kit.run_state import Tree


def test_build_nests_alpha_sub_under_alpha(forest_home):
    claude_mds, _ = walk.find_projects(forest_home, paths.skip_names(), on_progress=lambda _n: None)

    trees = forest.build(claude_mds)

    by_path = {tree.path: tree for tree in trees}
    alpha = by_path[forest_home / "alpha"]
    assert alpha.name == "Meridian Logbook"
    assert len(alpha.subtrees) == 1
    assert alpha.subtrees[0].path == forest_home / "alpha" / "sub"
    assert alpha.subtrees[0].name == "Meridian Logbook — Tidal Module"
    assert forest_home / "alpha" / "sub" not in by_path


def test_build_names_fall_back_to_dir_name_without_heading(tmp_path):
    project = tmp_path / "noheading"
    project.mkdir()
    (project / "CLAUDE.md").write_text("just prose, no heading\n", encoding="utf-8")

    trees = forest.build([project / "CLAUDE.md"])

    assert trees[0].name == "noheading"


def test_apply_selection_inherits_to_subtrees():
    child = Tree(path=Path("/a/child"), name="child", claude_md=Path("/a/child/CLAUDE.md"))
    parent = Tree(path=Path("/a"), name="a", claude_md=Path("/a/CLAUDE.md"), subtrees=[child])
    other = Tree(path=Path("/b"), name="b", claude_md=Path("/b/CLAUDE.md"))

    count = forest.apply_selection([parent, other], {str(Path("/a"))})

    assert parent.selected is True
    assert child.selected is True
    assert other.selected is False
    assert count == 2


def test_apply_selection_can_select_a_subtree_without_its_parent():
    child = Tree(path=Path("/a/child"), name="child", claude_md=Path("/a/child/CLAUDE.md"))
    parent = Tree(path=Path("/a"), name="a", claude_md=Path("/a/CLAUDE.md"), subtrees=[child])

    count = forest.apply_selection([parent], {str(Path("/a/child"))})

    assert parent.selected is False
    assert child.selected is True
    assert count == 1
