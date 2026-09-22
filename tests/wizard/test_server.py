"""Tests for cc_interproject.wizard.server against a real server on a real port: the page render, the
token gate, the loopback Host/Origin gate, unknown paths, and the quit shutdown.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from cc_interproject.run_state import Run
from cc_interproject.wizard import server


def make_run(home: Path, mode: str = "install") -> Run:
    return Run(mode=mode, home=home, claude_dir=home / "dot-claude", root=home, no_browser=True)


def start_server(run: Run):
    httpd = server.make_server(run)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread


def request(httpd, path, method="GET", body=None, token=None, headers=None):
    """Send one request and return `(status, text)`; a refusal comes back the same way."""
    url = f"http://127.0.0.1:{httpd.server_address[1]}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token is not None:
        req.add_header("X-Kit-Token", token)
    for name, value in (headers or {}).items():
        req.add_header(name, value)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode("utf-8")


@pytest.fixture
def running(forest_home, fake_claude_on_path):
    run = make_run(forest_home)
    httpd, thread = start_server(run)
    yield run, httpd, thread
    httpd.shutdown()
    httpd.server_close()
    thread.join(3)


def test_page_needs_the_token(running):
    _run, httpd, _thread = running
    assert request(httpd, "/")[0] == 403
    assert request(httpd, "/?t=not-the-token")[0] == 403


def test_page_inlines_assets_and_token(running):
    run, httpd, _thread = running
    status, body = request(httpd, f"/?t={run.token}")
    assert status == 200
    assert f'window.KIT_TOKEN = "{run.token}"' in body
    assert "<!--@css-->" not in body
    assert "<!--@js-->" not in body
    assert "<!--@js2-->" not in body
    assert "<!--@icons-->" not in body
    assert ".badge-waiting" in body
    assert "icon-welcome" in body
    assert "function renderForest(" in body
    assert "function subtreeList(" in body


def test_api_needs_the_token_header(running):
    _run, httpd, _thread = running
    assert request(httpd, "/api/state")[0] == 403
    assert request(httpd, "/api/state", token="not-the-token")[0] == 403


def test_api_accepts_the_token_header(running):
    run, httpd, _thread = running
    status, body = request(httpd, "/api/state", token=run.token)
    assert status == 200
    assert json.loads(body)["mode"] == "install"


def test_foreign_origin_is_refused(running):
    run, httpd, _thread = running
    headers = {"Origin": "http://evil.example"}
    assert request(httpd, "/api/state", token=run.token, headers=headers)[0] == 403
    own = {"Origin": f"http://127.0.0.1:{httpd.server_address[1]}"}
    assert request(httpd, "/api/state", token=run.token, headers=own)[0] == 200


def test_foreign_host_is_refused(running):
    run, httpd, _thread = running
    headers = {"Host": "evil.example"}
    assert request(httpd, "/api/state", token=run.token, headers=headers)[0] == 403


def test_unknown_path_is_404(running):
    run, httpd, _thread = running
    assert request(httpd, "/api/nowhere", token=run.token)[0] == 404
    assert request(httpd, "/favicon.ico", token=run.token)[0] == 404


def test_quit_with_body_token_stops_the_server(running):
    run, httpd, thread = running
    status, body = request(httpd, "/api/quit", method="POST", body={"token": run.token})
    assert status == 200
    assert json.loads(body) == {"ok": True}
    thread.join(3)
    assert not thread.is_alive()


def test_render_page_substitutes_every_slot():
    page = server.render_page("abc123")
    assert 'window.KIT_TOKEN = "abc123"' in page
    assert "%%TOKEN%%" not in page
    for slot, _name in server._ASSET_SLOTS:
        assert slot not in page, f"{slot} was left unsubstituted"
    assert page.index("function renderForest(") > page.index("function kitFetch(")
