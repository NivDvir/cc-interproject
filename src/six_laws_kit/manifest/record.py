"""Builds, writes, loads, and hashes the kit's install manifest
(`~/.claude/six-laws.manifest.json`, schema 1 — see DESIGN.md §5).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from pathlib import Path

from six_laws_kit import VERSION, paths
from six_laws_kit.run_state import Run

KIT_URL = "https://github.com/six-laws-kit/six-laws-kit"


def new(run: Run, stamp: str, previous: dict | None = None) -> dict:
    """Build a manifest header for `run`, stamped at `stamp`.

    Without `previous`, `entries` starts empty and `installed_at` is the plain stamp, exactly as
    a first-ever install. With `previous` (a manifest loaded from a prior install), `entries` is
    seeded with every one of its entries whose target still exists on disk — so a re-install's
    idempotent steps, which record nothing themselves, do not make `--uninstall` forget them — and
    `installed_at` becomes the list of every install's stamp, oldest first. `apply.execute`
    deduplicates entries by path once the new run's own actions have been recorded, so a target
    touched again this run keeps only its freshest entry.
    """
    return {
        "schema": 1,
        "kit_name": paths.KIT_NAME,
        "kit_version": VERSION,
        "url": KIT_URL,
        "installed_at": _installed_at(previous, stamp),
        "modules": sorted(run.modules),
        "python": platform.python_version(),
        "platform": platform.system(),
        "hook_interpreter": paths.hook_interpreter(),
        "backup_dir": str(paths.backups_dir(run.claude_dir, stamp)),
        "entries": _seed_entries(previous),
        "heads": _heads(run),
    }


def _installed_at(previous: dict | None, stamp: str) -> str | list[str]:
    if previous is None:
        return stamp
    history = previous.get("installed_at")
    if isinstance(history, list):
        return [*history, stamp]
    return [history, stamp] if history else [stamp]


def _seed_entries(previous: dict | None) -> list[dict]:
    if previous is None:
        return []
    return [entry for entry in previous.get("entries", []) if _entry_target_exists(entry)]


def _entry_target_exists(entry: dict) -> bool:
    path = entry.get("path")
    return bool(path) and Path(path).exists()


def dedupe_entries(entries: list[dict]) -> list[dict]:
    """Collapse `entries` to one per `path`, keeping each path's LAST occurrence (its freshest
    recorded state) at that occurrence's original position. A target seeded from a previous
    install and then rewritten this run ends up represented only by the new entry.
    """
    last_index_for_path: dict[str, int] = {}
    for index, entry in enumerate(entries):
        path = entry.get("path")
        if path is not None:
            last_index_for_path[path] = index
    keep = set(last_index_for_path.values())
    return [entry for index, entry in enumerate(entries) if index in keep or entry.get("path") is None]


def _heads(run: Run) -> list[dict]:
    return [
        {"path": path_str, "written_by": row.written_by, "status": row.status, "seconds": row.seconds}
        for path_str, row in run.rows.items()
    ]


def add_entry(manifest: dict, entry: dict) -> None:
    """Append `entry` to `manifest["entries"]` in place."""
    manifest["entries"].append(entry)


def write(manifest: dict, path: Path) -> None:
    """Write `manifest` to `path` atomically, with a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    os.replace(tmp, path)


def load(path: Path) -> dict | None:
    """Return the manifest at `path`, or `None` if it is missing or unreadable."""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"six-laws-kit: could not read manifest {path}: {exc}", file=sys.stderr)  # noqa: T201
        return None


def sha256(path: Path) -> str:
    """Return the hex sha256 digest of `path`'s current bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
