"""The wizard's loopback HTTP server: one page and twelve JSON endpoints on `127.0.0.1`, a random
port, and a per-run token that every request must carry. `render_page` inlines the CSS, both JS
files and the icons into `assets/index.html` so the page needs no follow-up request and works
offline.

Nothing here is logged to stdout; set `KIT_DEBUG` to get one request line per call on stderr.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from cc_interproject import paths
from cc_interproject.run_state import Run
from cc_interproject.wizard import api

IDLE_TIMEOUT_SECONDS = 15 * 60
IDLE_CHECK_SECONDS = 15
SHUTDOWN_DELAY_SECONDS = 0.3
MAX_BODY_BYTES = 1 << 20

_ASSET_SLOTS = (
    ("<!--@css-->", "wizard.css"),
    ("<!--@js-->", "wizard.js"),
    ("<!--@js2-->", "wizard2.js"),
    ("<!--@icons-->", "icons.svg"),
)
_TOKEN_SLOT = "%%TOKEN%%"

_ROUTES = {
    ("GET", "/api/state"): lambda run, body: api.state(run),
    ("POST", "/api/scan"): lambda run, body: api.scan_start(run),
    ("GET", "/api/scan"): lambda run, body: api.scan_progress(run),
    ("POST", "/api/selection"): lambda run, body: api.set_selection(run, body.get("selected") or []),
    ("POST", "/api/heads"): lambda run, body: api.heads_start(run),
    ("GET", "/api/heads"): lambda run, body: api.heads_progress(run),
    ("GET", "/api/plan"): lambda run, body: api.plan(run),
    ("POST", "/api/install"): lambda run, body: api.install_start(run, bool(body.get("confirm"))),
    ("GET", "/api/install"): lambda run, body: api.install_progress(run),
    ("GET", "/api/done"): lambda run, body: api.done(run),
    ("POST", "/api/quit"): lambda run, body: api.quit(run),
}
_ACCEPTED_ROUTES = {("POST", "/api/scan"), ("POST", "/api/heads"), ("POST", "/api/install")}
_QUIT_ROUTE = ("POST", "/api/quit")


def make_server(run: Run) -> ThreadingHTTPServer:
    """Bind a server on `127.0.0.1:0` for this run, issuing its token if it has none yet, and start
    the idle watchdog. The caller serves it (see `launch.open_ui`) and closes it when done.
    """
    if not run.token:
        run.token = secrets.token_hex(16)
    api.QUIT_REQUESTED.clear()
    httpd = _WizardServer(("127.0.0.1", 0), _Handler, run)
    threading.Thread(target=_watch_idle, args=(httpd,), daemon=True).start()
    return httpd


def render_page(token: str) -> str:
    """Return the complete page: `assets/index.html` with its CSS, JS and icons inlined and the
    per-run token substituted into the one inline script.
    """
    page = read_asset("index.html")
    for slot, name in _ASSET_SLOTS:
        page = page.replace(slot, read_asset(name))
    return page.replace(_TOKEN_SLOT, token)


def read_asset(name: str) -> str:
    """Read one file from `wizard/assets/`, from the source tree or from inside the zipapp."""
    return paths.read_package_resource(__package__, f"assets/{name}")


class _WizardServer(ThreadingHTTPServer):
    """A `ThreadingHTTPServer` that carries the run, the time of the last request, and the flag
    the idle watchdog stops on.
    """

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, run: Run) -> None:
        super().__init__(address, handler)
        self.wizard_run = run
        self.last_request = time.monotonic()
        self.stopping = threading.Event()

    def server_close(self) -> None:
        self.stopping.set()
        super().server_close()


def _watch_idle(httpd: _WizardServer) -> None:
    while not httpd.stopping.wait(IDLE_CHECK_SECONDS):
        if time.monotonic() - httpd.last_request > IDLE_TIMEOUT_SECONDS:
            httpd.shutdown()
            return


def _status_for(method: str, path: str, result: dict) -> int:
    if (method, path) == ("POST", "/api/install") and "error" in result:
        return 409
    if (method, path) in _ACCEPTED_ROUTES:
        return 202
    return 200


class _Handler(BaseHTTPRequestHandler):
    """Routes one request. Every check it makes is in its own small method: loopback Host/Origin,
    then the token, then the dispatch table.
    """

    server_version = "cc-interproject"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's naming
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler's naming
        self._handle("POST")

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - overrides the stdlib signature
        if os.environ.get("KIT_DEBUG"):
            sys.stderr.write(f"cc-interproject: {self.address_string()} {format % args}\n")

    def _handle(self, method: str) -> None:
        self.server.last_request = time.monotonic()
        parsed = urlparse(self.path)
        if not self._loopback_ok():
            self._send_json(403, {"error": "request refused: not a loopback caller"})
            return
        if method == "GET" and parsed.path == "/":
            self._serve_page(parsed.query)
            return
        route = _ROUTES.get((method, parsed.path))
        if route is None:
            self._send_json(404, {"error": "no such endpoint"})
            return
        body = self._read_body()
        if not self._token_ok(method, parsed.path, body):
            self._send_json(403, {"error": "request refused: bad token"})
            return
        result = route(self.server.wizard_run, body)
        self._send_json(_status_for(method, parsed.path, result), result)
        if (method, parsed.path) == _QUIT_ROUTE:
            threading.Timer(SHUTDOWN_DELAY_SECONDS, self.server.shutdown).start()

    def _serve_page(self, query: str) -> None:
        token = (parse_qs(query).get("t") or [""])[0]
        if not self._matches_token(token):
            self._send_text(403, "Forbidden.")
            return
        self._send_text(200, render_page(token), "text/html; charset=utf-8")

    def _loopback_ok(self) -> bool:
        port = self.server.server_address[1]
        host = self.headers.get("Host", "")
        if host not in {f"127.0.0.1:{port}", f"localhost:{port}", "127.0.0.1", "localhost"}:
            return False
        origin = self.headers.get("Origin")
        return origin is None or origin in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}

    def _token_ok(self, method: str, path: str, body: dict) -> bool:
        if self._matches_token(self.headers.get("X-Kit-Token", "")):
            return True
        if (method, path) != _QUIT_ROUTE:
            return False
        return self._matches_token(str(body.get("token", "")))

    def _matches_token(self, candidate: str) -> bool:
        expected = self.server.wizard_run.token
        return bool(expected) and secrets.compare_digest(candidate, expected)

    def _read_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return {}
        if length <= 0 or length > MAX_BODY_BYTES:
            return {}
        try:
            parsed = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _send_json(self, status: int, payload: dict) -> None:
        self._send_text(status, json.dumps(payload), "application/json; charset=utf-8")

    def _send_text(self, status: int, text: str, content_type: str = "text/plain; charset=utf-8") -> None:
        data = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)
