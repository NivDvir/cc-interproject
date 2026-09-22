"""Command-line entry point: parses arguments, builds a `Run`, and dispatches to `--uninstall`,
`--status`, or the install/dry-run wizard (browser UI, falling back to the terminal when none can
be opened). See `docs/DESIGN.md` section 2 for the full data flow.

Exit codes: 0 ok, 2 bad arguments, 3 the `claude` CLI was not found, 4 `claude` is not logged in,
5 an error occurred while writing files, 6 the user aborted (Ctrl-C, or "no" at a prompt).

Testing aid: setting `KIT_SKIP_AUTH` skips the `claude` login check, but only in `--dry-run` mode
(dry-run never writes anything, so a fake `claude` with no real account is enough to exercise it).
"""

from __future__ import annotations

import argparse
import os
import sys

from six_laws_kit import VERSION
from six_laws_kit.heads import preflight
from six_laws_kit.manifest import status, uninstall
from six_laws_kit.run_state import Run, new_run
from six_laws_kit.wizard import launch, terminal

EXIT_OK = 0
EXIT_BAD_ARGS = 2
EXIT_NO_CLAUDE = 3
EXIT_NOT_LOGGED_IN = 4
EXIT_ABORTED = 6

KIT_SKIP_AUTH = "KIT_SKIP_AUTH"


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser: one mutually exclusive mode flag (`--dry-run` / `--uninstall` /
    `--status`, default plain install), plus the modifiers documented in `docs/INTERFACES.md`.
    """
    parser = argparse.ArgumentParser(
        prog="six-laws-kit", description="Install the six-law setup for Claude Code projects."
    )
    parser.add_argument("--version", action="version", version=f"six-laws-kit {VERSION}")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Render the install plan; write nothing.")
    mode.add_argument("--uninstall", action="store_true", help="Undo a previous install.")
    mode.add_argument("--status", action="store_true", help="Report what is currently installed.")
    parser.add_argument(
        "--restore-backups", action="store_true", help="With --uninstall, also restore backed-up files."
    )
    parser.add_argument("--no-browser", action="store_true", help="Skip the browser UI; use the terminal.")
    parser.add_argument("--root", metavar="DIR", help="Scan root other than $HOME (testing).")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        return _dispatch(argv)
    except KeyboardInterrupt:
        print("\nsix-laws-kit: aborted", file=sys.stderr)
        return EXIT_ABORTED


def _dispatch(argv: list[str] | None) -> int:
    args = build_parser().parse_args(argv)
    run = new_run(args)
    if run.mode in ("install", "dry-run"):
        code = _preflight(run)
        if code is not None:
            return code
    if run.mode == "uninstall":
        _status_line("uninstalling")
        return uninstall.run(run, args.restore_backups)
    if run.mode == "status":
        _status_line("checking status")
        return status.run(run)
    return _run_wizard(run)


def _preflight(run: Run) -> int | None:
    _status_line("locating claude")
    if preflight.find_claude(run) is None:
        print("six-laws-kit: the claude CLI was not found on PATH", file=sys.stderr)
        return EXIT_NO_CLAUDE
    preflight.probe_capabilities(run)
    if run.mode == "dry-run" and os.environ.get(KIT_SKIP_AUTH):
        return None
    _status_line("checking authentication")
    if not preflight.auth_ping(run):
        print("six-laws-kit: claude is not logged in (run `claude /login`)", file=sys.stderr)
        return EXIT_NOT_LOGGED_IN
    return None


def _run_wizard(run: Run) -> int:
    if run.no_browser or not launch.can_open_browser():
        _status_line("starting the terminal installer")
        return terminal.run(run)
    _status_line("starting the browser installer")
    code = launch.open_ui(run)
    if code == launch.EXIT_NO_BROWSER:
        _status_line("no browser could be opened; falling back to the terminal")
        return terminal.run(run)
    return code


def _status_line(message: str) -> None:
    print(f"six-laws-kit: {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
