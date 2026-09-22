"""`run(run, restore_backups, ask)` loads the manifest under `run.claude_dir` and undoes its
`entries[]` in reverse, per DESIGN.md §5: delete an unmodified created file (else ask); strip an
unmodified marker block and undo its recorded blank-line/trailing-newline addition (report if it
was modified since, leave alone if the markers are gone); remove exactly the hook dicts this kit
added from `settings.json`, never rewriting the rest of the file; restore a plain appended line's
pre-install bytes from its backup when unmodified (else ask). `--restore-backups` runs a second,
blunter pass that copies every file under the manifest's `backup_dir` back over its original
location.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Callable

from six_laws_kit import paths
from six_laws_kit.manifest import record
from six_laws_kit.run_state import Run
from six_laws_kit.write import blocks, settings


def run(run: Run, restore_backups: bool = False, ask: Callable[[str], bool] | None = None) -> int:
    """Undo whatever the manifest under `run.claude_dir` says this kit installed. Returns 0
    whether or not there was anything to undo; problems are reported on stderr.
    """
    ask_fn = ask if ask is not None else _default_ask
    manifest_path = paths.manifest_path(run.claude_dir)
    manifest = record.load(manifest_path)
    if manifest is None:
        print(f"six-laws-kit: nothing installed under {run.claude_dir}", file=sys.stderr)  # noqa: T201
        return 0
    for entry in reversed(manifest.get("entries", [])):
        _undo_entry(entry, ask_fn)
    if restore_backups:
        _restore_all_backups(manifest, run.root)
    with contextlib.suppress(OSError):
        manifest_path.unlink()
    return 0


def _default_ask(message: str) -> bool:
    answer = input(f"{message} [y/N] ")
    return answer.strip().lower() in ("y", "yes")


def _undo_entry(entry: dict, ask: Callable[[str], bool]) -> None:
    kind = entry.get("kind")
    if kind == "created_file":
        _undo_created_file(entry, ask)
    elif kind == "inserted_block":
        _undo_inserted_block(entry)
    elif kind == "settings_hooks":
        _undo_settings_hooks(entry)
    elif kind == "backup":
        _undo_backup(entry, ask)
    elif kind == "created_dir":
        _undo_created_dir(entry)


def _undo_created_dir(entry: dict) -> None:
    path = Path(entry["path"])
    if not path.is_dir():
        return
    with contextlib.suppress(OSError):
        path.rmdir()  # only succeeds when empty; a non-empty dir is left alone


def _undo_created_file(entry: dict, ask: Callable[[str], bool]) -> None:
    path = Path(entry["path"])
    if not path.exists():
        return
    if record.sha256(path) == entry.get("sha256_after"):
        path.unlink()
        return
    if ask(f"{path} has changed since install; delete anyway?"):
        path.unlink()
    else:
        print(f"six-laws-kit: left changed file: {path}", file=sys.stderr)  # noqa: T201


def _undo_inserted_block(entry: dict) -> None:
    path = Path(entry["path"])
    if not path.exists():
        print(f"six-laws-kit: markers gone, file missing: {path}", file=sys.stderr)  # noqa: T201
        return
    with path.open(encoding="utf-8", newline="") as handle:
        text = handle.read()
    current_sha = record.sha256(path)
    new_text, found = blocks.strip(text, entry["marker_id"])
    if not found:
        print(f"six-laws-kit: markers not found exactly once, left as is: {path}", file=sys.stderr)  # noqa: T201
        return
    if entry.get("trailing_newline_added") and current_sha == entry.get("sha256_after"):
        new_text = _trim_one_trailing_newline(new_text)
    _write_atomic(path, new_text)
    if current_sha != entry.get("sha256_after"):
        message = f"six-laws-kit: block had changed since install, stripped anyway: {path}"
        print(message, file=sys.stderr)  # noqa: T201


def _trim_one_trailing_newline(text: str) -> str:
    if text.endswith("\r\n"):
        return text[:-2]
    if text.endswith("\n"):
        return text[:-1]
    return text


def _undo_settings_hooks(entry: dict) -> None:
    path = Path(entry["path"])
    if not path.exists():
        return
    current = settings.load(path)
    commands = [added["command"] for added in entry.get("added", [])]
    new_settings = settings.remove_hooks(current, commands)
    _write_atomic(path, json.dumps(new_settings, indent=2) + "\n")


def _undo_backup(entry: dict, ask: Callable[[str], bool]) -> None:
    path = Path(entry["path"])
    if not path.exists():
        return
    if entry.get("sha256_after") and record.sha256(path) == entry["sha256_after"]:
        _restore_single_backup(entry)
        return
    if ask(f"{path} has changed since install; restore its pre-install content anyway?"):
        _restore_single_backup(entry)
    else:
        print(f"six-laws-kit: left changed file: {path}", file=sys.stderr)  # noqa: T201


def _restore_single_backup(entry: dict) -> None:
    path = Path(entry["path"])
    backup_path = entry.get("backup_path")
    if not backup_path:
        if path.exists():
            path.unlink()
        return
    backup = Path(backup_path)
    if backup.exists():
        _write_atomic_bytes(path, backup.read_bytes())


def _restore_all_backups(manifest: dict, root: Path) -> None:
    backup_dir = Path(manifest.get("backup_dir", ""))
    if not backup_dir.exists():
        return
    for backup_file in sorted(backup_dir.rglob("*")):
        if backup_file.is_file():
            rel = backup_file.relative_to(backup_dir)
            _write_atomic_bytes(root / rel, backup_file.read_bytes())


def _write_atomic(target: Path, text: str) -> None:
    _write_atomic_bytes(target, text.encode("utf-8"))


def _write_atomic_bytes(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    with tmp.open("wb") as handle:
        handle.write(data)
    os.replace(tmp, target)
