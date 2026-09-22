"""Shared run state: the dataclasses every category reads and writes, and the two functions that
build a Run from parsed CLI arguments and flatten its selected trees.
"""

from __future__ import annotations

import argparse
import threading
from dataclasses import dataclass, field
from pathlib import Path

from cc_interproject import paths


@dataclass
class Tree:
    path: Path
    name: str
    claude_md: Path
    has_session: bool = False
    last_session: str | None = None
    subtrees: list[Tree] = field(default_factory=list)
    selected: bool = False


@dataclass
class Row:
    name: str
    owns: str
    asks_others_to_watch_for: str
    contact_subject: str
    written_by: str
    status: str
    seconds: float = 0.0


@dataclass
class Action:
    kind: str
    target: Path
    marker_id: str | None
    payload: str
    existing_text: str | None
    diff: str
    existed: bool


@dataclass
class Run:
    mode: str
    home: Path
    claude_dir: Path
    root: Path
    no_browser: bool
    claude_bin: str | None = None
    claude_caps: dict[str, bool] = field(default_factory=dict)
    auth_ok: bool = False
    trees: list[Tree] = field(default_factory=list)
    rows: dict[str, Row] = field(default_factory=dict)
    ask_progress: dict[str, str] = field(default_factory=dict)
    scan_progress: dict[str, object] = field(default_factory=dict)
    plan: list[Action] = field(default_factory=list)
    install_progress: dict[str, object] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    step: str = "welcome"
    token: str = ""
    confirmed: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)


def new_run(args: argparse.Namespace) -> Run:
    """Build a Run from parsed CLI arguments.

    `home` is `paths.home_dir()` (an explicit `HOME` override, else the real `Path.home()`).
    `root` is that same directory unless `--root` was given, in which case `claude_dir` moves to
    `root/"dot-claude"` instead of `home/".claude"` — the testing convention that keeps a fixture
    forest's own `.claude` stand-in out of the way of the real one.
    """
    home = paths.home_dir()
    root_arg = getattr(args, "root", None)
    root = Path(root_arg) if root_arg else home
    claude_dir = root / "dot-claude" if root != home else home / ".claude"
    return Run(
        mode=_resolve_mode(args),
        home=home,
        claude_dir=claude_dir,
        root=root,
        no_browser=bool(getattr(args, "no_browser", False)),
    )


def _resolve_mode(args: argparse.Namespace) -> str:
    if getattr(args, "status", False):
        return "status"
    if getattr(args, "uninstall", False):
        return "uninstall"
    if getattr(args, "dry_run", False):
        return "dry-run"
    return "install"


def selected_trees(run: Run) -> list[Tree]:
    """Flatten `run.trees` into the selected subset only, in tree order."""
    result: list[Tree] = []
    for tree in run.trees:
        _collect_selected(tree, result)
    return result


def _collect_selected(tree: Tree, result: list[Tree]) -> None:
    if tree.selected:
        result.append(tree)
    for subtree in tree.subtrees:
        _collect_selected(subtree, result)
