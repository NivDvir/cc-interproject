"""Tests for cc_interproject.heads.preflight against fixtures/claude_fake/claude."""

from __future__ import annotations

from cc_interproject.heads import preflight
from cc_interproject.run_state import Run


def _make_run(tmp_path):
    return Run(
        mode="dry-run",
        home=tmp_path,
        claude_dir=tmp_path / ".claude",
        root=tmp_path,
        no_browser=True,
    )


def test_find_claude_sets_bin(fake_claude_on_path, tmp_path):
    run = _make_run(tmp_path)
    found = preflight.find_claude(run)
    assert found is not None
    assert run.claude_bin == found
    assert "claude" in found


def test_find_claude_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    run = _make_run(tmp_path)
    found = preflight.find_claude(run)
    assert found is None
    assert run.claude_bin is None


def test_probe_capabilities_true_for_fake(fake_claude_on_path, tmp_path):
    run = _make_run(tmp_path)
    preflight.find_claude(run)
    caps = preflight.probe_capabilities(run)
    assert caps["json_schema"] is True
    assert run.claude_caps["json_schema"] is True


def test_probe_capabilities_without_bin(tmp_path):
    run = _make_run(tmp_path)
    run.claude_bin = None
    caps = preflight.probe_capabilities(run)
    assert caps == {"json_schema": False}


def test_auth_ping_ok(fake_claude_on_path, tmp_path):
    run = _make_run(tmp_path)
    preflight.find_claude(run)
    assert preflight.auth_ping(run) is True
    assert run.auth_ok is True


def test_auth_ping_authfail(fake_claude_on_path, tmp_path, monkeypatch):
    monkeypatch.setenv("KIT_FAKE_MODE", "authfail")
    run = _make_run(tmp_path)
    preflight.find_claude(run)
    assert preflight.auth_ping(run) is False
    assert run.auth_ok is False


def test_auth_ping_without_bin(tmp_path):
    run = _make_run(tmp_path)
    run.claude_bin = None
    assert preflight.auth_ping(run) is False
    assert run.auth_ok is False
