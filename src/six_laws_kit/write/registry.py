"""Renders `PROJECT_REGISTRY.md`'s table: one row per selected tree, in tree order, sourced from
the `Row`s the Heads step collected (or `NOT STATED` placeholders for a tree with none).
"""

from __future__ import annotations

from datetime import datetime, timezone

from six_laws_kit.run_state import Row, Tree

_COLUMNS = (
    "Project",
    "Path",
    "Owns",
    "Asks others to watch for",
    "Contact subject",
    "Written by",
    "Updated",
)


def render(rows: dict[str, Row], trees: list[Tree], header: str) -> str:
    """Return the header text followed by a blank line and the registry markdown table."""
    lines = [header.rstrip("\n"), "", _header_row(), _separator_row()]
    today = _today()
    for tree in _flatten(trees):
        lines.append(_row_line(tree, rows.get(str(tree.path)), today))
    return "\n".join(lines) + "\n"


def _today() -> str:
    return datetime.now(tz=timezone.utc).date().isoformat()


def _header_row() -> str:
    return "| " + " | ".join(_COLUMNS) + " |"


def _separator_row() -> str:
    return "|" + "|".join(["---"] * len(_COLUMNS)) + "|"


def _row_line(tree: Tree, row: Row | None, today: str) -> str:
    if row is not None:
        cells = [
            row.name,
            str(tree.path),
            row.owns,
            row.asks_others_to_watch_for,
            row.contact_subject,
            row.written_by,
        ]
    else:
        cells = [tree.name, str(tree.path), "NOT STATED", "NOT STATED", "NOT STATED", "installer"]
    escaped = [_escape(cell) for cell in cells] + [today]
    return "| " + " | ".join(escaped) + " |"


def _escape(cell: str) -> str:
    return cell.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ")


def _flatten(trees: list[Tree]) -> list[Tree]:
    flat: list[Tree] = []
    for tree in trees:
        flat.append(tree)
        flat.extend(_flatten(tree.subtrees))
    return flat
