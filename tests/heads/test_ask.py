"""Tests for cc_interproject.heads.ask against fixtures/claude_fake/claude and fixtures/forest/alpha."""

from __future__ import annotations

import time
from pathlib import Path

from cc_interproject.heads import ask
from cc_interproject.run_state import Run, Tree

FOREST = Path(__file__).resolve().parents[2] / "fixtures" / "forest"


def _alpha_tree() -> Tree:
    return Tree(path=FOREST / "alpha", name="alpha", claude_md=FOREST / "alpha" / "CLAUDE.md")


def _make_run(tmp_path, selected_paths):
    trees = []
    for path in selected_paths:
        trees.append(Tree(path=path, name=path.name, claude_md=path / "CLAUDE.md", selected=True))
    return Run(
        mode="dry-run",
        home=tmp_path,
        claude_dir=tmp_path / ".claude",
        root=tmp_path,
        no_browser=True,
        trees=trees,
    )


def test_is_auth_failure_text():
    assert ask.is_auth_failure_text("Not logged in. Please run /login")
    assert ask.is_auth_failure_text("INVALID API KEY")
    assert ask.is_auth_failure_text("Authentication required")
    assert not ask.is_auth_failure_text("")
    assert not ask.is_auth_failure_text("all good")


def test_parse_row_structured_output():
    envelope = '{"type": "result", "structured_output": {"name": "Alpha", "owns": "x"}}'
    assert ask.parse_row(envelope) == {"name": "Alpha", "owns": "x"}


def test_parse_row_fenced_json_in_result():
    envelope = '{"type": "result", "result": "```json\\n{\\"name\\": \\"Alpha\\"}\\n```"}'
    assert ask.parse_row(envelope) == {"name": "Alpha"}


def test_parse_row_balanced_object_in_prose():
    envelope = '{"result": "Sure, here it is: {\\"name\\": \\"Alpha\\"} thanks"}'
    assert ask.parse_row(envelope) == {"name": "Alpha"}


def test_parse_row_unparsable():
    assert ask.parse_row('{"result": "I cannot help with that."}') is None
    assert ask.parse_row("not json at all") is None


def test_row_from_fields_falls_back_to_tree_name_when_name_not_stated():
    envelope = '{"structured_output": {"name": "NOT STATED", "owns": "the api gateway"}}'
    fields = ask.parse_row(envelope)
    tree = Tree(path=Path("/tmp/api"), name="api", claude_md=Path("/tmp/api/CLAUDE.md"))
    row = ask._row_from_fields(fields, tree, 1.0)
    assert row.name == "api"
    assert row.written_by == "self"


def test_ask_one_ok(fake_claude_on_path):
    tree = _alpha_tree()
    row = ask.ask_one("claude", tree, json_schema=True, timeout=30)
    assert row.status == "ok"
    assert row.written_by == "self"
    assert row.name == "Meridian Logbook"


def test_ask_one_noschema(fake_claude_on_path, monkeypatch):
    monkeypatch.setenv("KIT_FAKE_MODE", "noschema")
    tree = _alpha_tree()
    row = ask.ask_one("claude", tree, json_schema=False, timeout=30)
    assert row.status == "ok"
    assert row.written_by == "self"
    assert row.name == "Meridian Logbook"


def test_ask_one_garbage(fake_claude_on_path, monkeypatch):
    monkeypatch.setenv("KIT_FAKE_MODE", "garbage")
    tree = _alpha_tree()
    row = ask.ask_one("claude", tree, json_schema=True, timeout=30)
    assert row.status == "fallback"
    assert row.written_by == "installer"


def test_ask_one_authfail(fake_claude_on_path, monkeypatch):
    monkeypatch.setenv("KIT_FAKE_MODE", "authfail")
    tree = _alpha_tree()
    row = ask.ask_one("claude", tree, json_schema=True, timeout=30)
    assert row.status == "authfail"
    assert row.written_by == "installer"


def test_ask_one_nonzero(fake_claude_on_path, monkeypatch):
    monkeypatch.setenv("KIT_FAKE_MODE", "nonzero")
    tree = _alpha_tree()
    row = ask.ask_one("claude", tree, json_schema=True, timeout=30)
    assert row.status == "error"
    assert row.written_by == "installer"


def test_ask_one_slow_times_out_quickly(fake_claude_on_path, monkeypatch):
    monkeypatch.setenv("KIT_FAKE_MODE", "slow")
    monkeypatch.setenv("KIT_FAKE_SLEEP", "3")
    tree = _alpha_tree()
    started = time.time()
    row = ask.ask_one("claude", tree, json_schema=True, timeout=1)
    elapsed = time.time() - started
    assert row.status == "timeout"
    assert row.written_by == "installer"
    assert elapsed < 2.5


def test_ask_one_missing_binary(tmp_path):
    tree = Tree(path=tmp_path, name=tmp_path.name, claude_md=tmp_path / "CLAUDE.md")
    row = ask.ask_one(str(tmp_path / "no-such-claude"), tree, json_schema=True, timeout=5)
    assert row.status == "error"
    assert row.written_by == "installer"


def test_start_completes_for_selected_trees(fake_claude_on_path, tmp_path):
    run = _make_run(tmp_path, [FOREST / "alpha", FOREST / "beta"])
    run.claude_bin = "claude"
    run.claude_caps = {"json_schema": True}

    ask.start(run, max_workers=2, timeout=30)

    deadline = time.time() + 30
    while time.time() < deadline and not ask.all_done(run):
        time.sleep(0.2)

    assert ask.all_done(run) is True
    assert len(run.rows) == 2
    for tree in run.trees:
        row = run.rows[str(tree.path)]
        assert row.status == "ok"
        assert row.written_by == "self"
