"""The eleven actions behind the wizard's HTTP endpoints. Each takes the `Run`, mutates it under
`run.lock` where it must, and returns a plain dict the server serialises as JSON. The two long
steps — the forest scan and the install — run on daemon threads and report through a lock-guarded
progress dict that the page polls.
"""

from __future__ import annotations

import subprocess
import threading
from dataclasses import asdict

from six_laws_kit import paths
from six_laws_kit.discover import forest, sessions, walk
from six_laws_kit.heads import ask, fallback, preflight
from six_laws_kit.run_state import Action, Run, Tree, selected_trees
from six_laws_kit.texts import loader
from six_laws_kit.write import apply as write_apply
from six_laws_kit.write import plan as write_plan

UNINSTALL_COMMAND = "python3 install.py --uninstall"
ACCOUNT_POINTER_SPLIT = "\n\n---"
VERSION_PROBE_TIMEOUT = 15

QUIT_REQUESTED = threading.Event()
"""Set by `quit()`. The server reads it to know the page asked the installer to stop."""

_CLAUDE_VERSIONS: dict[str, str] = {}


def state(run: Run) -> dict:
    """The whole picture the page needs at any step: mode, home, and the scanned forest."""
    with run.lock:
        payload = {
            "step": run.step,
            "mode": run.mode,
            "dry_run": run.mode == "dry-run",
            "home": str(run.home),
            "trees": [_tree_dict(tree) for tree in run.trees],
        }
    payload["claude_version"] = _claude_version(run)
    return payload


def scan_start(run: Run) -> dict:
    """Start the forest scan on a daemon thread. Returns immediately; poll `scan_progress`."""
    with run.lock:
        if run.scan_progress.get("running"):
            return {"started": False}
        run.step = "scan"
        run.scan_progress = {"done": False, "dirs_seen": 0, "skipped_roots": [], "running": True}
    threading.Thread(target=_scan, args=(run,), daemon=True).start()
    return {"started": True}


def scan_progress(run: Run) -> dict:
    """The live scan counters: `{done, dirs_seen, skipped_roots}`."""
    with run.lock:
        progress = dict(run.scan_progress)
    return {
        "done": bool(progress.get("done")),
        "dirs_seen": int(progress.get("dirs_seen") or 0),
        "skipped_roots": list(progress.get("skipped_roots") or []),
    }


def set_selection(run: Run, selected: list[str]) -> dict:
    """Apply the page's checked top-level paths; subtrees inherit their parent's selection."""
    with run.lock:
        count = forest.apply_selection(run.trees, set(selected))
        run.step = "heads"
    return {"selected": count}


def heads_start(run: Run) -> dict:
    """Ask every selected project for its own registry row, in parallel, in the background."""
    if not run.claude_bin:
        preflight.find_claude(run)
        preflight.probe_capabilities(run)
    trees = selected_trees(run)
    with run.lock:
        run.step = "heads"
        for tree in trees:
            run.ask_progress.setdefault(str(tree.path), "waiting")
    if not run.claude_bin:
        _fill_fallback_rows(run, trees)
        return {"started": False, "reason": "the claude CLI was not found; rows came from each CLAUDE.md"}
    ask.start(run)
    return {"started": True}


def heads_progress(run: Run) -> dict:
    """One entry per selected project: its ask state, elapsed seconds, and its row once it has one."""
    trees = selected_trees(run)
    with run.lock:
        progress = dict(run.ask_progress)
        rows = dict(run.rows)
    results = []
    for tree in trees:
        key = str(tree.path)
        row = rows.get(key)
        entry = {"path": key, "status": progress.get(key, "waiting"), "seconds": row.seconds if row else 0.0}
        if row is not None:
            entry["row"] = asdict(row)
        results.append(entry)
    return {"done": ask.all_done(run), "results": results}


def plan(run: Run) -> dict:
    """Build the install plan and return it for the Review step. Nothing is written here."""
    actions = write_plan.build(run)
    with run.lock:
        run.step = "review"
    return {"actions": [_action_dict(action) for action in actions], "warnings": _warnings(run)}


def install_start(run: Run, confirm: bool) -> dict:
    """Start the install on a daemon thread. Returns an `error` dict (the server answers 409)
    when the page did not confirm, or when this is a dry run and nothing may be written.
    """
    if not confirm:
        return {"error": "The install was not confirmed."}
    if run.mode == "dry-run":
        return {"error": "Dry run: the plan was rendered and nothing is written."}
    if not run.plan:
        write_plan.build(run)
    with run.lock:
        if run.install_progress.get("running"):
            return {"started": False}
        run.confirmed = True
        run.step = "install"
        run.install_progress = {
            "done": False,
            "current": "",
            "completed": 0,
            "total": len(run.plan),
            "errors": [],
            "running": True,
        }
    threading.Thread(target=_install, args=(run,), daemon=True).start()
    return {"started": True}


def install_progress(run: Run) -> dict:
    """The live install counters: `{done, current, completed, total, errors}`."""
    with run.lock:
        progress = dict(run.install_progress)
    return {
        "done": bool(progress.get("done")),
        "current": str(progress.get("current") or ""),
        "completed": int(progress.get("completed") or 0),
        "total": int(progress.get("total") or 0),
        "errors": list(progress.get("errors") or []),
    }


def done(run: Run) -> dict:
    """The closing screen: the block only the user can paste into their account instructions, where
    the manifest went, how to undo it, and how many projects answered for themselves.
    """
    with run.lock:
        rows = list(run.rows.values())
        run.step = "done"
    self_rows = sum(1 for row in rows if row.written_by == "self")
    return {
        "paste_block": _paste_block(),
        "manifest_path": str(paths.manifest_path(run.claude_dir)),
        "uninstall_cmd": UNINSTALL_COMMAND,
        "self_rows": self_rows,
        "installer_rows": len(rows) - self_rows,
    }


def quit(run: Run) -> dict:
    """Record that the page is finished. The server shuts itself down shortly after answering."""
    with run.lock:
        run.step = "done"
    QUIT_REQUESTED.set()
    return {"ok": True}


def _scan(run: Run) -> None:
    counter = {"dirs_seen": 0}

    def on_progress(dirs_seen: int) -> None:
        counter["dirs_seen"] = dirs_seen
        with run.lock:
            run.scan_progress["dirs_seen"] = dirs_seen

    try:
        claude_mds, skipped = walk.find_projects(run.root, paths.skip_names(), on_progress)
    except OSError as exc:
        with run.lock:
            run.errors.append(f"scan failed: {exc}")
            run.scan_progress.update({"done": True, "running": False})
        return
    trees = forest.build(claude_mds)
    sessions.annotate(trees, run.claude_dir)
    with run.lock:
        run.trees = trees
        run.scan_progress = {
            "done": True,
            "dirs_seen": counter["dirs_seen"],
            "skipped_roots": [str(path) for path in skipped],
            "running": False,
        }


def _install(run: Run) -> None:
    def on_progress(target: str, completed: int, total: int) -> None:
        with run.lock:
            run.install_progress["current"] = target
            run.install_progress["completed"] = completed
            run.install_progress["total"] = total

    try:
        write_apply.execute(run, on_progress)
    except OSError as exc:
        _record_install_error(run, str(exc))
    finally:
        with run.lock:
            run.install_progress["done"] = True
            run.install_progress["running"] = False


def _record_install_error(run: Run, message: str) -> None:
    with run.lock:
        errors = run.install_progress.setdefault("errors", [])
        if isinstance(errors, list):
            errors.append(message)
        run.errors.append(message)


def _fill_fallback_rows(run: Run, trees: list[Tree]) -> None:
    for tree in trees:
        row = fallback.row_from_claude_md(tree.claude_md, 0.0, "error")
        with run.lock:
            run.rows[str(tree.path)] = row
            run.ask_progress[str(tree.path)] = "fallback"


def _tree_dict(tree: Tree) -> dict:
    return {
        "path": str(tree.path),
        "name": tree.name,
        "has_session": tree.has_session,
        "last_session": tree.last_session,
        "selected": tree.selected,
        "subtrees": [_tree_dict(subtree) for subtree in tree.subtrees],
    }


def _action_dict(action: Action) -> dict:
    return {
        "kind": action.kind,
        "target": str(action.target),
        "existed": action.existed,
        "diff": action.diff,
        "bytes": len(action.payload.encode("utf-8")),
    }


def _warnings(run: Run) -> list[str]:
    warnings: list[str] = []
    if run.mode == "dry-run":
        warnings.append("Dry run: this plan is shown for review only and nothing will be written.")
    borrowed = sum(1 for row in run.rows.values() if row.written_by != "self")
    if borrowed:
        warnings.append(
            f"{borrowed} project(s) could not answer for themselves; their row was written from "
            "their own CLAUDE.md instead."
        )
    warnings.extend(run.errors)
    return warnings


def _paste_block() -> str:
    """Part (b) of `texts/ACCOUNT_POINTER.md` — everything after the `---` line. Part (a) is the
    one-line pointer the plan appends to `~/.claude/CLAUDE.md`; only part (b) is pasted by hand.
    """
    text = loader.read("ACCOUNT_POINTER.md")
    _part_a, separator, part_b = text.partition(ACCOUNT_POINTER_SPLIT)
    return part_b.strip() if separator else text.strip()


def _claude_version(run: Run) -> str:
    """`claude --version`, probed once per binary and cached. Empty when no CLI was located."""
    binary = run.claude_bin
    if not binary:
        return ""
    if binary not in _CLAUDE_VERSIONS:
        _CLAUDE_VERSIONS[binary] = _probe_version(binary)
    return _CLAUDE_VERSIONS[binary]


def _probe_version(binary: str) -> str:
    try:
        proc = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=VERSION_PROBE_TIMEOUT
        )
    except (subprocess.TimeoutExpired, OSError):
        return ""
    return (proc.stdout or "").strip()
