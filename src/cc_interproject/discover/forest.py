"""Build the nested project forest from discovered `CLAUDE.md` paths, and apply a selection set
with inheritance down to subtrees.
"""

from __future__ import annotations

from pathlib import Path

from cc_interproject.run_state import Tree

_HEADING_PREFIX = "# "


def build(claude_mds: list[Path]) -> list[Tree]:
    """Return top-level Trees; a `CLAUDE.md` inside another project's directory becomes a
    subtree of the nearest project above it, never a root of its own. Sorted by depth then by
    path (as a stable tie-break for same-depth entries) so the numbered list a user picks from
    does not depend on the filesystem's own, OS-dependent directory-entry order.
    """
    top_level: list[Tree] = []
    for claude_md in sorted(claude_mds, key=lambda p: (len(p.parent.parts), p.parent.as_posix())):
        project_dir = claude_md.parent
        tree = Tree(path=project_dir, name=_read_name(claude_md), claude_md=claude_md)
        parent = _nearest_ancestor(top_level, project_dir)
        if parent is None:
            top_level.append(tree)
        else:
            parent.subtrees.append(tree)
    return top_level


def apply_selection(trees: list[Tree], selected: set[str]) -> int:
    """Mark trees selected per `selected` (a set of `str(tree.path)`), cascading a parent's
    selection down to every subtree. Returns the total number of trees now selected.
    """
    count = 0
    for tree in trees:
        count += _apply_selection_one(tree, selected, inherited=False)
    return count


def _apply_selection_one(tree: Tree, selected: set[str], inherited: bool) -> int:
    is_selected = inherited or str(tree.path) in selected
    tree.selected = is_selected
    count = 1 if is_selected else 0
    for subtree in tree.subtrees:
        count += _apply_selection_one(subtree, selected, inherited=is_selected)
    return count


def _nearest_ancestor(trees: list[Tree], path: Path) -> Tree | None:
    best: Tree | None = None
    for tree in trees:
        if not _is_ancestor(tree.path, path):
            continue
        candidate = _nearest_ancestor(tree.subtrees, path) or tree
        if best is None or len(candidate.path.parts) > len(best.path.parts):
            best = candidate
    return best


def _is_ancestor(maybe_parent: Path, path: Path) -> bool:
    if maybe_parent == path:
        return False
    try:
        path.relative_to(maybe_parent)
    except ValueError:
        return False
    return True


def _read_name(claude_md: Path) -> str:
    try:
        text = claude_md.read_text(encoding="utf-8")
    except OSError:
        return claude_md.parent.name
    for line in text.splitlines():
        if line.startswith(_HEADING_PREFIX):
            return line[len(_HEADING_PREFIX) :].strip()
    return claude_md.parent.name
