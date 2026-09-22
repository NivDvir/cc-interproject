"""Tests for run_state.py: new_run's home/root/claude_dir resolution, and selected_trees's
flattening.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cc_interproject import run_state
from cc_interproject.run_state import Tree


def _args(**overrides):
    defaults = {
        "dry_run": False,
        "uninstall": False,
        "status": False,
        "no_browser": False,
        "root": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def test_new_run_defaults_to_home_and_dot_claude(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))

    run = run_state.new_run(_args())

    assert run.home == fake_home
    assert run.root == fake_home
    assert run.claude_dir == fake_home / ".claude"
    assert run.mode == "install"


def test_new_run_with_root_uses_dot_claude_subdir(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: fake_home))
    test_root = tmp_path / "forest"
    test_root.mkdir()

    run = run_state.new_run(_args(root=str(test_root)))

    assert run.root == test_root
    assert run.claude_dir == test_root / "dot-claude"


def test_new_run_mode_flags():
    assert run_state.new_run(_args(dry_run=True)).mode == "dry-run"
    assert run_state.new_run(_args(uninstall=True)).mode == "uninstall"
    assert run_state.new_run(_args(status=True)).mode == "status"


def test_selected_trees_flattens_in_tree_order():
    child = Tree(path=Path("/a/child"), name="child", claude_md=Path("/a/child/CLAUDE.md"), selected=True)
    parent = Tree(path=Path("/a"), name="a", claude_md=Path("/a/CLAUDE.md"), selected=True, subtrees=[child])
    other = Tree(path=Path("/b"), name="b", claude_md=Path("/b/CLAUDE.md"), selected=False)
    run = run_state.Run(
        mode="install",
        home=Path("/home"),
        claude_dir=Path("/home/.claude"),
        root=Path("/home"),
        no_browser=False,
        trees=[parent, other],
    )

    assert run_state.selected_trees(run) == [parent, child]
