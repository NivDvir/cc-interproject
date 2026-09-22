from __future__ import annotations

import re
from pathlib import Path

from six_laws_kit.run_state import Row, Tree
from six_laws_kit.write import registry

HEADER = "# Project registry\n\nRead before any cross-project work.\n"


def _tree(path: str, name: str) -> Tree:
    return Tree(path=Path(path), name=name, claude_md=Path(path) / "CLAUDE.md")


def test_render_starts_with_header_then_table_header_and_separator():
    text = registry.render({}, [_tree("/home/alpha", "Alpha")], HEADER)
    lines = text.splitlines()
    assert lines[0] == "# Project registry"
    header_index = next(i for i, line in enumerate(lines) if line.startswith("| Project"))
    assert "Written by" in lines[header_index]
    assert "Updated" in lines[header_index]
    assert set(lines[header_index + 1]) <= set("|-")


def test_row_uses_row_fields_when_present_and_escapes_pipes():
    alpha = _tree("/home/alpha", "Alpha")
    row = Row(
        name="Alpha",
        owns="Ships | cargo handling",
        asks_others_to_watch_for="port closures",
        contact_subject="alpha",
        written_by="self",
        status="ok",
    )
    text = registry.render({str(alpha.path): row}, [alpha], HEADER)
    data_line = [line for line in text.splitlines() if line.startswith("| Alpha")][0]
    assert "Ships \\| cargo handling" in data_line
    assert "self" in data_line
    assert re.search(r"\d{4}-\d{2}-\d{2} \|$", data_line)


def test_row_falls_back_to_not_stated_when_no_row_for_the_tree():
    beta = _tree("/home/beta", "Beta")
    text = registry.render({}, [beta], HEADER)
    data_line = [line for line in text.splitlines() if line.startswith("| Beta")][0]
    assert data_line.count("NOT STATED") == 3
    assert "installer" in data_line


def test_rows_are_emitted_in_tree_order_including_nested_subtrees():
    alpha = _tree("/home/alpha", "Alpha")
    sub = _tree("/home/alpha/sub", "Alpha Sub")
    alpha.subtrees.append(sub)
    beta = _tree("/home/beta", "Beta")
    text = registry.render({}, [alpha, beta], HEADER)
    data_lines = [line for line in text.splitlines() if line.startswith("|") and "---" not in line][1:]
    names = [line.split("|")[1].strip() for line in data_lines]
    assert names == ["Alpha", "Alpha Sub", "Beta"]
