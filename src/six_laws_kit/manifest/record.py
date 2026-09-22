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


def new(run: Run, stamp: str) -> dict:
    """Build a fresh manifest header (empty `entries`) for `run`, stamped at `stamp`."""
    return {
        "schema": 1,
        "kit_name": paths.KIT_NAME,
        "kit_version": VERSION,
        "url": KIT_URL,
        "installed_at": stamp,
        "modules": sorted(run.modules),
        "python": platform.python_version(),
        "platform": platform.system(),
        "hook_interpreter": paths.hook_interpreter(),
        "backup_dir": str(paths.backups_dir(run.claude_dir, stamp)),
        "entries": [],
        "heads": _heads(run),
    }


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
