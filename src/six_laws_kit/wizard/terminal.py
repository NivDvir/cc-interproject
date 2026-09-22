"""The no-browser install flow: the same six steps the browser wizard walks through (Welcome,
Scan, Heads, Review, Install, Done), driven on stdin/stdout instead of HTTP. Talks to the
running install only through `wizard.api`, the same surface the HTTP layer calls, and renders the
Review step's diffs itself from `api.plan`'s plain-dict actions — the same way `wizard/assets/
wizard.js` renders them for the browser, so no cross-category import is needed here.
"""

from __future__ import annotations

import sys
import time

from six_laws_kit.run_state import Run
from six_laws_kit.wizard import api

WELCOME_TEXT = (
    "This installer looks at the Claude Code projects on this computer, asks each one you choose\n"
    "a single question about itself, and then writes a small set of shared files so every project\n"
    "can find and recognize the others. Nothing is written until you confirm the exact changes on\n"
    "the Review step."
)
COST_NOTE = "Cost note: one short Claude call per chosen project, on your account."
SCAN_POLL_SECONDS = 0.4
HEADS_POLL_SECONDS = 0.7
INSTALL_POLL_SECONDS = 0.3
EXIT_OK = 0
EXIT_INSTALL_ERROR = 5
EXIT_ABORTED = 6
RULER = "=" * 60


def run(run: Run) -> int:
    """Drive all six steps to completion. EOF on a required prompt (or a declined confirmation)
    aborts and returns 6; an install error returns 5; otherwise 0.
    """
    try:
        return _run_steps(run)
    except EOFError:
        print("\nsix-laws-kit: aborted (no input)", file=sys.stderr)
        return EXIT_ABORTED


def _run_steps(run: Run) -> int:
    _step_welcome()
    state = _step_scan(run)
    _step_selection(run, state.get("trees") or [])
    _step_heads(run)
    code = _step_review(run)
    if code is not None:
        return code
    return _step_install_and_done(run)


def _step_welcome() -> None:
    print(WELCOME_TEXT)
    print(COST_NOTE)
    print()


def _step_scan(run: Run) -> dict:
    print("Scanning for Claude Code projects", end="", flush=True)
    api.scan_start(run)
    _poll_dots(lambda: api.scan_progress(run))
    state = api.state(run)
    trees = state.get("trees") or []
    print(f"Found {len(trees)} project(s):")
    for line in _render_forest(trees):
        print(line)
    return state


def _poll_dots(fetch) -> dict:
    progress = fetch()
    while not progress.get("done"):
        print(".", end="", flush=True)
        time.sleep(SCAN_POLL_SECONDS)
        progress = fetch()
    print()
    return progress


def _render_forest(trees: list[dict]) -> list[str]:
    lines: list[str] = []
    for index, tree in enumerate(trees, start=1):
        lines.append(f"  [{index}] {_tree_label(tree)}")
        lines.extend(_render_subtrees(tree.get("subtrees") or [], indent=6))
    return lines


def _render_subtrees(subtrees: list[dict], indent: int) -> list[str]:
    lines: list[str] = []
    pad = " " * indent
    for subtree in subtrees:
        lines.append(f"{pad}{_tree_label(subtree)}")
        lines.extend(_render_subtrees(subtree.get("subtrees") or [], indent + 2))
    return lines


def _tree_label(tree: dict) -> str:
    name = tree.get("name", "?")
    if tree.get("has_session"):
        return f"{name} (last session {tree.get('last_session')})"
    return f"{name} (no prior session)"


def _step_selection(run: Run, trees: list[dict]) -> None:
    line = _read_line('Select projects to include (numbers, e.g. "1 3", or "all"): ')
    selected = _parse_selection(line, trees)
    api.set_selection(run, selected)


def _parse_selection(line: str, trees: list[dict]) -> list[str]:
    if line.strip().lower() == "all":
        return [tree["path"] for tree in trees]
    selected = []
    for token in line.split():
        if token.isdigit() and 1 <= int(token) <= len(trees):
            selected.append(trees[int(token) - 1]["path"])
    return selected


def _step_heads(run: Run) -> None:
    print("Registering heads (each chosen project answers once)...")
    api.heads_start(run)
    seen: dict[str, str] = {}
    progress = api.heads_progress(run)
    while True:
        for row in progress.get("results") or []:
            _print_head_change(row, seen)
        if progress.get("done"):
            return
        time.sleep(HEADS_POLL_SECONDS)
        progress = api.heads_progress(run)


def _print_head_change(row: dict, seen: dict[str, str]) -> None:
    path, status = row.get("path"), row.get("status")
    if seen.get(path) == status:
        return
    seen[path] = status
    print(f"  {path}: {status}")


def _step_review(run: Run) -> int | None:
    print("Review the changes. Nothing has been written yet.")
    result = api.plan(run)
    for warning in result.get("warnings") or []:
        print(f"warning: {warning}")
    print(_render_actions(result.get("actions") or []))
    if run.mode == "dry-run":
        print("Dry run: nothing written.")
        return EXIT_OK
    if not _confirm("Apply?", default_yes=False):
        return EXIT_ABORTED
    return None


def _render_actions(actions: list[dict]) -> str:
    lines: list[str] = []
    for action in actions:
        if action.get("kind") == "create_file" and action.get("existed"):
            lines.append(f"kept existing: {action.get('target')}")
            continue
        diff = action.get("diff") or ""
        if not diff:
            lines.append(f"{action.get('kind')}: {action.get('target')} (no change)")
            continue
        lines.append(f"{action.get('kind')}: {action.get('target')}")
        lines.append(diff)
    return "\n".join(lines)


def _step_install_and_done(run: Run) -> int:
    print("Installing...")
    api.install_start(run, confirm=True)
    progress = api.install_progress(run)
    while not progress.get("done"):
        current = progress.get("current") or "Working..."
        print(f"  {current} ({progress.get('completed', 0)}/{progress.get('total', 0)})")
        time.sleep(INSTALL_POLL_SECONDS)
        progress = api.install_progress(run)
    if progress.get("errors"):
        for error in progress["errors"]:
            print(f"six-laws-kit: install error: {error}", file=sys.stderr)
        return EXIT_INSTALL_ERROR
    return _step_done(run)


def _step_done(run: Run) -> int:
    result = api.done(run)
    print(
        f"{result.get('self_rows', 0)} project(s) answered for themselves; "
        f"{result.get('installer_rows', 0)} used a fallback."
    )
    print(f"Manifest written to {result.get('manifest_path')}")
    print(RULER)
    print(result.get("paste_block", ""))
    print(RULER)
    print(f"To remove everything this installer wrote: {result.get('uninstall_cmd')}")
    return EXIT_OK


def _read_line(prompt: str, default: str | None = None) -> str:
    """Read one line. EOF or a blank answer falls back to `default` when one is given; EOF with
    no default propagates so `run` can treat the whole session as aborted.
    """
    try:
        answer = input(prompt).strip()
    except EOFError:
        if default is None:
            raise
        return default
    return answer or (default if default is not None else "")


def _confirm(question: str, default_yes: bool) -> bool:
    hint = "[Y/n]" if default_yes else "[y/N]"
    default = "y" if default_yes else "n"
    answer = _read_line(f"{question} {hint}: ", default=default).lower()
    return answer in ("y", "yes")
