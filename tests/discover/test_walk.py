"""Tests for discover/walk.py: skip-list enforcement, project discovery, the depth cap, and
symlink safety.
"""

from __future__ import annotations

import os
from pathlib import Path

from six_laws_kit import paths
from six_laws_kit.discover import walk


def test_walk_finds_every_top_level_and_nested_project(forest_home):
    claude_mds, _ = walk.find_projects(forest_home, paths.skip_names(), on_progress=lambda _n: None)

    found = {p.parent.relative_to(forest_home) for p in claude_mds}

    assert Path("alpha") in found
    assert Path("alpha/sub") in found
    assert Path("beta") in found
    assert Path("dot-claude") in found


def test_walk_skips_vendored_and_housekeeping_dirs(forest_home):
    claude_mds, skipped_roots = walk.find_projects(
        forest_home, paths.skip_names(), on_progress=lambda _n: None
    )

    found = {p.parent.relative_to(forest_home) for p in claude_mds}
    assert Path("alpha/node_modules/pkg") not in found
    assert Path("beta/.venv/lib") not in found
    assert Path(".Trash/old") not in found

    skipped_names = {p.name for p in skipped_roots}
    assert {"node_modules", ".venv", ".Trash"} <= skipped_names


def test_walk_respects_depth_cap(tmp_path):
    current = tmp_path
    for level in range(5):
        current = current / f"level{level}"
        current.mkdir()
    (current / "CLAUDE.md").write_text("# Deep\n", encoding="utf-8")

    claude_mds, _ = walk.find_projects(tmp_path, set(), on_progress=lambda _n: None, max_depth=2)

    assert claude_mds == []


def test_walk_symlink_loop_does_not_hang(tmp_path):
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "CLAUDE.md").write_text("# Real\n", encoding="utf-8")
    loop = real_dir / "loop"
    os.symlink(real_dir, loop, target_is_directory=True)

    claude_mds, _ = walk.find_projects(tmp_path, set(), on_progress=lambda _n: None)

    found = {p.parent for p in claude_mds}
    assert real_dir in found
    assert loop not in found


def test_walk_calls_on_progress_every_200_dirs(tmp_path):
    for index in range(450):
        (tmp_path / f"d{index}").mkdir()
    seen: list[int] = []

    walk.find_projects(tmp_path, set(), on_progress=seen.append)

    # root (1) + 450 children = 451 directories visited; the interval calls fire at 200 and 400,
    # then one final unconditional call reports the exact total.
    assert seen == [200, 400, 451]


def test_walk_skips_claude_worktrees_and_build_checkouts(tmp_path):
    real_project = tmp_path / "x"
    real_project.mkdir()
    (real_project / "CLAUDE.md").write_text("# Real Project\n", encoding="utf-8")
    worktree_project = tmp_path / "x" / ".claude" / "worktrees" / "w"
    worktree_project.mkdir(parents=True)
    (worktree_project / "CLAUDE.md").write_text("# Worktree Copy\n", encoding="utf-8")
    build_checkout = tmp_path / "y" / ".build" / "checkouts" / "c"
    build_checkout.mkdir(parents=True)
    (build_checkout / "CLAUDE.md").write_text("# Build Checkout\n", encoding="utf-8")

    claude_mds, _ = walk.find_projects(tmp_path, paths.skip_names(), on_progress=lambda _n: None)

    found = {p.parent for p in claude_mds}
    assert real_project in found
    assert worktree_project not in found
    assert build_checkout not in found


def test_walk_final_progress_call_reports_exact_total(forest_home):
    skip = paths.skip_names()
    seen: list[int] = []

    walk.find_projects(forest_home, skip, on_progress=seen.append)

    assert seen[-1] > 0
    assert seen[-1] == _count_dirs_honoring_skip(forest_home, skip)


def _count_dirs_honoring_skip(root: Path, skip: set[str]) -> int:
    """Independently count the directories `find_projects` should visit: `root` itself plus
    every descendant not pruned by `skip`, mirroring its skip-at-every-level rule without
    reusing its internals.
    """
    count = 0
    for _dirpath, dirnames, _filenames in os.walk(root):
        count += 1
        dirnames[:] = [name for name in dirnames if name not in skip]
    return count
