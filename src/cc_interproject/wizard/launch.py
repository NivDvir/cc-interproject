"""Open the wizard in the user's own browser and serve it until the page says it is done.

Exit codes returned to `cli.main`: 0 the wizard finished, 6 the user interrupted it with Ctrl-C,
7 no browser could be opened here — the caller falls back to `wizard.terminal`. The URL is always
printed to stderr first, so it can be opened by hand whatever happens next.
"""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

from cc_interproject.run_state import Run
from cc_interproject.wizard import server

EXIT_OK = 0
EXIT_INTERRUPTED = 6
EXIT_NO_BROWSER = 7

WSL_MARKER = "microsoft"
PROC_VERSION = Path("/proc/version")
DISPLAY_VARIABLES = ("DISPLAY", "WAYLAND_DISPLAY")


def can_open_browser(run: Run | None = None) -> bool:
    """True when a browser can reasonably be opened here.

    False under WSL (where a Linux browser is usually absent and the Windows one cannot reach the
    loopback port reliably), false on Linux with no display server, and false when the run was
    started with `--no-browser`. The `run` argument is optional so the environment alone can be
    tested; `INTERFACES.md` lists the no-argument form.
    """
    if run is not None and run.no_browser:
        return False
    if _is_wsl():
        return False
    if sys.platform.startswith("linux"):
        return any(os.environ.get(name) for name in DISPLAY_VARIABLES)
    return True


def open_ui(run: Run) -> int:
    """Start the server, open the page, and block in `serve_forever` until the page quits.

    Returns EXIT_NO_BROWSER (7) without serving when no browser can be opened, so `cli.main` can
    run the terminal flow instead.
    """
    httpd = server.make_server(run)
    url = f"http://127.0.0.1:{httpd.server_address[1]}/?t={run.token}"
    print(f"cc-interproject: the installer is at {url}", file=sys.stderr)  # noqa: T201
    if not can_open_browser(run) or not _open_browser(url):
        httpd.server_close()
        return EXIT_NO_BROWSER
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        return EXIT_INTERRUPTED
    finally:
        httpd.server_close()
    return EXIT_OK


def _open_browser(url: str) -> bool:
    try:
        return webbrowser.open(url)
    except webbrowser.Error:
        return False


def _is_wsl() -> bool:
    try:
        return WSL_MARKER in PROC_VERSION.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return False
