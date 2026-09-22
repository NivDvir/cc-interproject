"""The whole wizard flow over HTTP against a real server and the fake `claude` binary: state,
scan, selection, heads, plan, install, done, quit — plus the dry-run refusal.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import pytest

from cc_interproject.heads import preflight
from cc_interproject.run_state import Run
from cc_interproject.wizard import server
from tests.wizard.test_server import make_run, request, start_server

POLL_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 0.2


def call(httpd, run: Run, path: str, method: str = "GET", body=None):
    """One authenticated call; returns `(status, payload)` with the JSON already parsed."""
    status, text = request(httpd, path, method=method, body=body, token=run.token)
    return status, json.loads(text) if text else {}


def poll_until_done(httpd, run: Run, path: str) -> dict:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    payload: dict = {}
    while time.monotonic() < deadline:
        _status, payload = call(httpd, run, path)
        if payload.get("done"):
            return payload
        time.sleep(POLL_INTERVAL_SECONDS)
    pytest.fail(f"{path} never reported done; last payload: {payload}")
    return payload


def hash_tree(root: Path) -> dict:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def flatten_paths(trees) -> set:
    found = set()
    for tree in trees:
        found.add(tree["path"])
        found |= flatten_paths(tree["subtrees"])
    return found


@pytest.fixture
def serving(forest_home, fake_claude_on_path):
    """A running server over a copy of the fixture forest, with the fake `claude` located."""
    run = make_run(forest_home, "install")
    preflight.find_claude(run)
    preflight.probe_capabilities(run)
    httpd, thread = start_server(run)
    yield run, httpd
    httpd.shutdown()
    httpd.server_close()
    thread.join(3)


def test_full_flow_installs_and_reports(serving, forest_home):
    run, httpd = serving

    status, initial = call(httpd, run, "/api/state")
    assert status == 200
    assert initial["mode"] == "install"
    assert initial["dry_run"] is False
    assert initial["trees"] == []
    assert initial["claude_version"].startswith("9.9.9")

    assert call(httpd, run, "/api/scan", method="POST")[0] == 202
    scan = poll_until_done(httpd, run, "/api/scan")
    assert scan["done"] is True

    _status, scanned = call(httpd, run, "/api/state")
    found = flatten_paths(scanned["trees"])
    for name in ("alpha", "alpha/sub", "beta", "dot-claude"):
        assert str(forest_home / name) in found
    assert str(forest_home / "alpha" / "node_modules" / "pkg") not in found

    alpha, beta = str(forest_home / "alpha"), str(forest_home / "beta")
    status, selection = call(httpd, run, "/api/selection", method="POST", body={"selected": [alpha, beta]})
    assert status == 200
    # alpha/sub inherits alpha's selection (discover.forest.apply_selection), so three are chosen.
    assert selection["selected"] == 3

    assert call(httpd, run, "/api/heads", method="POST")[0] == 202
    heads = poll_until_done(httpd, run, "/api/heads")
    assert len(heads["results"]) == 3
    assert {entry["status"] for entry in heads["results"]} == {"answered"}
    assert all(entry["row"]["written_by"] == "self" for entry in heads["results"])

    before = hash_tree(forest_home)
    status, planned = call(httpd, run, "/api/plan")
    assert status == 200
    assert planned["actions"]
    assert all(set(action) == {"kind", "target", "existed", "diff", "bytes"} for action in planned["actions"])
    assert hash_tree(forest_home) == before, "the Review step must not write anything"

    assert call(httpd, run, "/api/install", method="POST", body={"confirm": True})[0] == 202
    installed = poll_until_done(httpd, run, "/api/install")
    assert installed["errors"] == []
    assert installed["completed"] == installed["total"] > 0

    status, finished = call(httpd, run, "/api/done")
    assert status == 200
    assert finished["self_rows"] == 3
    assert finished["installer_rows"] == 0
    assert finished["uninstall_cmd"] == "python3 install.py --uninstall"
    assert Path(finished["manifest_path"]).is_file()
    assert "INTERPROJECT_LAWS.md" in finished["paste_block"]
    assert (forest_home / "dot-claude" / "INTERPROJECT_LAWS.md").is_file()

    status, quit_payload = call(httpd, run, "/api/quit", method="POST")
    assert (status, quit_payload) == (200, {"ok": True})


def test_dry_run_refuses_to_install(forest_home, fake_claude_on_path):
    run = make_run(forest_home, "dry-run")
    httpd, thread = start_server(run)
    try:
        _status, initial = call(httpd, run, "/api/state")
        assert initial["dry_run"] is True

        before = hash_tree(forest_home)
        status, refused = call(httpd, run, "/api/install", method="POST", body={"confirm": True})
        assert status == 409
        assert "error" in refused

        status, unconfirmed = call(httpd, run, "/api/install", method="POST", body={})
        assert status == 409
        assert "error" in unconfirmed

        assert hash_tree(forest_home) == before, "a dry run must write nothing"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(3)


def test_install_start_is_refused_without_confirmation_in_install_mode(forest_home, fake_claude_on_path):
    run = make_run(forest_home, "install")
    httpd, thread = start_server(run)
    try:
        before = hash_tree(forest_home)
        status, refused = call(httpd, run, "/api/install", method="POST", body={"confirm": False})
        assert status == 409
        assert "error" in refused
        assert hash_tree(forest_home) == before
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(3)


def test_render_page_is_reachable_from_the_same_module():
    assert "Claude Code Inter-Project Communication" in server.render_page("token")
