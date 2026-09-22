"""Tests for six_laws_kit.wizard.terminal: the same install flow as tests/wizard/test_api.py's
HTTP version, driven over scripted stdin instead. `fixtures/forest`'s three top-level projects
come back from `discover.walk.find_projects` as `beta`, `dot-claude`, `alpha` in that order on
this checkout (`alpha` alone has a subtree), so selecting "1 2" picks the two trees with no
subtree — exactly two selected projects, both answered by the fake `claude` as "self".
"""

from __future__ import annotations

from pathlib import Path

from six_laws_kit.heads import preflight
from six_laws_kit.manifest import record
from six_laws_kit.run_state import Run
from six_laws_kit.wizard import terminal


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
    _scripted_input(monkeypatch, ["2 3", "", "y"])

    code = terminal.run(run)

    assert code == 0
    manifest_path = forest_home / "dot-claude" / "six-laws.manifest.json"
    assert manifest_path.is_file()
    manifest = record.load(manifest_path)
    self_heads = [head for head in manifest["heads"] if head["written_by"] == "self"]
    assert len(self_heads) == 2

    registry_text = (forest_home / "dot-claude" / "PROJECT_REGISTRY.md").read_text(encoding="utf-8")
    assert registry_text.count("| self |") == 2


def test_eof_at_the_first_prompt_aborts(forest_home, fake_claude_on_path, monkeypatch):
    run = _make_run(forest_home, "install")
    preflight.find_claude(run)
    preflight.probe_capabilities(run)
    _scripted_input(monkeypatch, [])

    assert terminal.run(run) == 6
