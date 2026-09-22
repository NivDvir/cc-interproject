from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

from six_laws_kit.run_state import Run, Tree
from six_laws_kit.write import blocks, plan

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_FIXTURES_DIR = _REPO_ROOT / "fixtures"

_TEXTS = {
    "SIX_LAWS.md": "law text\n",
    "INTERPROJECT_PROTOCOL.md": "protocol text\n",
    "PRIOR_ART.md": "prior art text\n",
    "DISPATCHER_QUEUE.md": "queue text\n",
    "REGISTRY_HEADER.md": "# Project registry\n\nRead before any cross-project work.\n",
    "ACCOUNT_POINTER.md": "Read the six laws before any cross-project work.\n\n---\n\nmore prose here.\n",
    "PROJECT_POINTER.md": "Reach other projects only through their heads.\n",
    "PACKET_REMINDER.md": "Packet reminder text.\n",
}


@pytest.fixture(autouse=True)
def _fake_texts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("six_laws_kit.texts.loader.read", lambda name: _TEXTS[name])


@pytest.fixture
def _fake_hook_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(plan, "_read_hook_source", lambda name: f"#!/usr/bin/env python3\n# fake {name}\n")


def _make_run(home: Path, modules: set) -> Run:
    run = Run(
        mode="dry-run", home=home, claude_dir=home / "dot-claude", root=home, no_browser=True, modules=modules
    )
    alpha = Tree(path=home / "alpha", name="Alpha", claude_md=home / "alpha" / "CLAUDE.md", selected=True)
    beta = Tree(path=home / "beta", name="Beta", claude_md=home / "beta" / "CLAUDE.md", selected=True)
    run.trees = [alpha, beta]
    return run


def _hash_tree(root: Path) -> dict:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_build_writes_nothing_to_disk(forest_home: Path):
    run = _make_run(forest_home, {"laws"})
    before = _hash_tree(forest_home)
    plan.build(run)
    after = _hash_tree(forest_home)
    assert before == after


def test_build_creates_missing_law_files_and_the_registry(forest_home: Path):
    run = _make_run(forest_home, {"laws"})
    actions = plan.build(run)
    assert actions is run.plan
    created_names = {a.target.name for a in actions if a.kind == "create_file" and not a.existed}
    assert created_names == {
        "SIX_LAWS.md",
        "INTERPROJECT_PROTOCOL.md",
        "PRIOR_ART.md",
        "DISPATCHER_QUEUE.md",
        "PROJECT_REGISTRY.md",
    }
    for action in actions:
        if action.kind == "create_file" and not action.existed:
            assert action.diff != ""


def test_build_keeps_an_existing_law_file(forest_home: Path):
    (forest_home / "dot-claude" / "SIX_LAWS.md").write_text("already here\n", encoding="utf-8")
    run = _make_run(forest_home, {"laws"})
    actions = plan.build(run)
    kept = [a for a in actions if a.kind == "create_file" and a.target.name == "SIX_LAWS.md"]
    assert len(kept) == 1
    assert kept[0].existed is True
    assert "kept existing:" in plan.render_text(actions)


def test_build_appends_the_account_pointer_line_once(forest_home: Path):
    run = _make_run(forest_home, {"laws"})
    actions = plan.build(run)
    append_actions = [a for a in actions if a.kind == "append_line"]
    assert len(append_actions) == 1
    action = append_actions[0]
    assert action.target == forest_home / "dot-claude" / "CLAUDE.md"
    assert "Read the six laws" in action.payload

    (forest_home / "dot-claude" / "CLAUDE.md").write_text(action.payload, encoding="utf-8")
    run_again = _make_run(forest_home, {"laws"})
    actions_again = plan.build(run_again)
    assert [a for a in actions_again if a.kind == "append_line"] == []


def test_build_inserts_project_pointer_into_each_selected_tree(forest_home: Path):
    run = _make_run(forest_home, {"laws"})
    actions = plan.build(run)
    pointer_actions = [a for a in actions if a.kind == "insert_block" and a.marker_id == "project-pointer"]
    targets = {a.target for a in pointer_actions}
    assert targets == {forest_home / "alpha" / "CLAUDE.md", forest_home / "beta" / "CLAUDE.md"}
    for action in pointer_actions:
        assert action.existed is True
        assert blocks.contains(action.payload, "project-pointer")


def test_build_skips_a_tree_that_already_has_the_pointer_block(forest_home: Path):
    alpha_md = forest_home / "alpha" / "CLAUDE.md"
    body = _TEXTS["PROJECT_POINTER.md"]
    block = blocks.render("project-pointer", 1, body)
    existing = alpha_md.read_text(encoding="utf-8")
    new_text, _leading, _trailing = blocks.insert(existing, block)
    alpha_md.write_text(new_text, encoding="utf-8")

    run = _make_run(forest_home, {"laws"})
    actions = plan.build(run)
    pointer_targets = {
        a.target for a in actions if a.kind == "insert_block" and a.marker_id == "project-pointer"
    }
    assert alpha_md not in pointer_targets
    assert forest_home / "beta" / "CLAUDE.md" in pointer_targets


def test_build_without_routing_module_has_no_hook_actions(forest_home: Path):
    run = _make_run(forest_home, {"laws"})
    actions = plan.build(run)
    assert [a for a in actions if a.kind in ("copy_hook_file", "merge_hooks")] == []


def test_build_with_routing_module_copies_hooks_and_merges_settings(
    forest_home: Path, _fake_hook_sources: None
):
    run = _make_run(forest_home, {"laws", "routing"})
    actions = plan.build(run)
    hook_actions = [a for a in actions if a.kind == "copy_hook_file"]
    hook_names = {a.target.name for a in hook_actions}
    assert hook_names == {"packet_reminder.py", "labor_tally.py", "load_cap.py", "PACKET_REMINDER.md"}
    for action in hook_actions:
        assert action.target.as_posix().endswith(f"hooks/six-laws/{action.target.name}")

    merge_actions = [a for a in actions if a.kind == "merge_hooks"]
    assert len(merge_actions) == 1
    settings_action = merge_actions[0]
    assert settings_action.target == forest_home / "dot-claude" / "settings.json"
    assert settings_action.existed is True
    assert "echo foreign" in settings_action.diff or "echo foreign" in (settings_action.existing_text or "")


def test_render_text_reports_kept_existing_and_diffs(forest_home: Path):
    run = _make_run(forest_home, {"laws"})
    actions = plan.build(run)
    text = plan.render_text(actions)
    assert "create_file:" in text
    assert "---" in text or "+++" in text


def _load_bundle_module():
    spec = importlib.util.spec_from_file_location("bundle_for_test_plan", _REPO_ROOT / "tools" / "bundle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_zipapp_dry_run_with_routing_lists_the_hook_files(forest_home: Path, tmp_path: Path):
    """Regression test: `_read_hook_source` used to join `Path(__file__).parent.parent / "hooks"`,
    which raises `NotADirectoryError` once the package runs from inside the zipapp bundle. Building
    the real archive and running it with routing on (the default) proves the `importlib.resources`
    fix works from inside a zip, not just from the source tree.
    """
    bundle = _load_bundle_module()
    archive = bundle.build(tmp_path / "dist")
    env = dict(os.environ)
    env["HOME"] = str(forest_home)
    env["PATH"] = f"{_FIXTURES_DIR / 'claude_fake'}{os.pathsep}{env.get('PATH', '')}"
    env["KIT_SKIP_AUTH"] = "1"
    env["KIT_FAKE_MODE"] = "ok"

    result = subprocess.run(
        [sys.executable, str(archive), "--dry-run", "--no-browser", "--root", str(forest_home)],
        env=env,
        input="all\n",
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    for hook_name in ("packet_reminder.py", "labor_tally.py", "load_cap.py"):
        assert hook_name in result.stdout, result.stdout
