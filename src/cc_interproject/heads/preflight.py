"""Checks run once, before any head is asked: find the `claude` CLI, probe which optional flags it
supports, and confirm it is logged in. See `docs/DESIGN.md` section 4.
"""

from __future__ import annotations

import shutil
import subprocess

from cc_interproject import paths
from cc_interproject.heads.ask import is_auth_failure_text
from cc_interproject.run_state import Run

CLAUDE_BIN_NAMES = ("claude", "claude.cmd")
AUTH_PING_PROMPT = "Reply with the single word OK."


def find_claude(run: Run) -> str | None:
    """Locate the `claude` CLI on PATH; record it on `run.claude_bin`."""
    for name in CLAUDE_BIN_NAMES:
        found = shutil.which(name)
        if found:
            run.claude_bin = found
            return found
    run.claude_bin = None
    return None


def probe_capabilities(run: Run) -> dict[str, bool]:
    """Run `<claude> --help` once; record which optional flags it supports on `run.claude_caps`."""
    caps = {"json_schema": False}
    if run.claude_bin:
        try:
            command = paths.windows_shim_argv([run.claude_bin, "--help"])
            proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
            output = (proc.stdout or "") + (proc.stderr or "")
            caps["json_schema"] = "--json-schema" in output
        except (subprocess.TimeoutExpired, OSError):
            caps["json_schema"] = False
    run.claude_caps = caps
    return caps


def auth_ping(run: Run, timeout: int = 60) -> bool:
    """Confirm the local `claude` CLI is authenticated; record the result on `run.auth_ok`."""
    if not run.claude_bin:
        run.auth_ok = False
        return False
    try:
        argv = [run.claude_bin, "-p", "--output-format", "json", "--max-turns", "1"]
        proc = subprocess.run(
            paths.windows_shim_argv(argv),
            cwd=run.home,
            input=AUTH_PING_PROMPT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        run.auth_ok = proc.returncode == 0 and not is_auth_failure_text(combined)
    except (subprocess.TimeoutExpired, OSError):
        run.auth_ok = False
    return run.auth_ok
