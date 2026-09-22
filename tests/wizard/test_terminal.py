"""Tests for cc_interproject.wizard.terminal: the same install flow as tests/wizard/test_api.py's
HTTP version, driven over scripted stdin instead. `fixtures/forest`'s three top-level projects
come back from `discover.walk.find_projects` as `beta`, `dot-claude`, `alpha` in that order on
this checkout (`alpha` alone has a subtree), so selecting "1 2" picks the two trees with no
subtree — exactly two selected projects, both answered by the fake `claude` as "self".
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from cc_interproject.heads import preflight
from cc_interproject.manifest import record
from cc_interproject.run_state import Run
from cc_interproject.wizard import terminal


def _make_run(home: Path, mode: str = "install") -> Run:
    return Run(mode=mode, home=home, claude_dir=home / "dot-claude", root=home, no_browser=True)


def _scripted_input(monkeypatch, lines: list[str]) -> None:
    remaining = list(lines)

    def fake_input(prompt: str = "") -> str:
        if not remaining:
            raise EOFError
        return remaining.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)


def test_install_flow_selects_two_projects_and_writes_the_manifest(
    forest_home, fake_claude_on_path, monkeypatch
):
    run = _make_run(forest_home, "install")
    preflight.find_claude(run)
    preflight.probe_capabilities(run)
    # Discovery is sorted (depth, then path) for a deterministic numbered list: [1] alpha,
    # [2] beta, [3] dot-claude. "2 3" picks the two projects with no subtree of their own, so
    # each numbered pick becomes exactly one self-written head; "1" would also cascade to
    # alpha's own subtree (alpha/sub), which is a separate, correct addressable project of its
    # own and is covered instead by test_walk_finds_every_top_level_and_nested_project.
    _scripted_input(monkeypatch, ["2 3", "y"])

    code = terminal.run(run)

    assert code == 0
    manifest_path = forest_home / "dot-claude" / "interproject.manifest.json"
    assert manifest_path.is_file()
    manifest = record.load(manifest_path)
    self_heads = [head for head in manifest["heads"] if head["written_by"] == "self"]
    assert len(self_heads) == 2

    registry_text = (forest_home / "dot-claude" / "PROJECT_REGISTRY.md").read_text(encoding="utf-8")
    assert registry_text.count("| self |") == 2


def _tree(name: str, path: str, subtrees=None) -> dict:
    return {
        "name": name,
        "path": path,
        "has_session": False,
        "last_session": None,
        "selected": False,
        "subtrees": subtrees or [],
    }


@pytest.fixture
def box_connectors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the box-drawing connectors, so a runner whose stdout is a code page without them (a
    Windows console) does not turn these rendering assertions into encoding assertions.
    """
    monkeypatch.setattr(terminal, "_connectors", lambda: terminal.BOX_CONNECTORS)


def test_forest_renders_each_tree_as_a_block_with_an_ascii_subtree(box_connectors):
    great = _tree("Ledger", "/h/code/platform/services/billing/ledger")
    grand = _tree("Billing", "/h/code/platform/services/billing", [great])
    child = _tree("Services", "/h/code/platform/services", [grand])
    trees = [_tree("Platform", "/h/code/platform", [child]), _tree("Webapp", "/h/code/webapp")]

    lines = terminal._render_forest(trees)

    assert lines[0].startswith("  [1] Platform")
    assert "3 subtrees" in lines[0]
    assert "/h/code/platform" in lines[0]
    assert lines[1] == "      └── Services  (/h/code/platform/services, no prior session)"
    assert lines[2].startswith("          └── Billing")
    assert lines[3].startswith("              └── Ledger")
    heads = [line for line in lines if line.startswith("  [")]
    assert len(heads) == 2
    assert "no subtrees" in heads[1]


def test_forest_uses_the_branch_connector_for_a_middle_subtree(box_connectors):
    trees = [
        _tree(
            "Mono",
            "/h/mono",
            [_tree("Ui", "/h/mono/ui", [_tree("Deep", "/h/mono/ui/deep")]), _tree("Core", "/h/mono/core")],
        )
    ]

    lines = terminal._render_forest(trees)

    assert lines[1].startswith("      ├── Ui")
    assert lines[2].startswith("      │   └── Deep")
    assert lines[3].startswith("      └── Core")


def test_forest_falls_back_to_ascii_when_stdout_cannot_encode_box_drawing(monkeypatch):
    """A cp1252 console would raise UnicodeEncodeError on the first connector and end the
    install, so the same shape is drawn with ASCII of identical widths instead.
    """
    monkeypatch.setattr(terminal.sys, "stdout", io.TextIOWrapper(io.BytesIO(), encoding="cp1252"))
    trees = [_tree("Mono", "/h/mono", [_tree("Ui", "/h/mono/ui"), _tree("Core", "/h/mono/core")])]

    lines = terminal._render_forest(trees)

    assert lines[1].startswith("      |-- Ui")
    assert lines[2].startswith("      `-- Core")
    widths = zip(terminal.BOX_CONNECTORS, terminal.ASCII_CONNECTORS)
    assert all(len(box) == len(plain) for box, plain in widths)


def test_eof_at_the_first_prompt_aborts(forest_home, fake_claude_on_path, monkeypatch):
    run = _make_run(forest_home, "install")
    preflight.find_claude(run)
    preflight.probe_capabilities(run)
    _scripted_input(monkeypatch, [])

    assert terminal.run(run) == 6
