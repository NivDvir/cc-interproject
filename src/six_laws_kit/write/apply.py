"""`execute(run, on_progress)` performs `run.plan`: creates directories, backs up any pre-existing
target under the manifest's backup directory, writes every change atomically, and records enough
in the manifest (via `manifest.record`) for `manifest.uninstall` to undo it later. On any `OSError`
mid-run, the manifest is written with whatever it has recorded so far, then the error is re-raised.

A re-install starts from the previous manifest (`record.new(..., previous=...)`) rather than a
blank one, so idempotent steps that record nothing this run (a law file already there, a pointer
block already present) do not make the second install's manifest forget the first install's files;
entries are deduplicated by path before writing, so a target this run did rewrite keeps only its
current entry.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from six_laws_kit import paths
from six_laws_kit.manifest import record
from six_laws_kit.run_state import Action, Run
from six_laws_kit.write import blocks, settings
from six_laws_kit.write.plan import MARKER_VERSION


def execute(run: Run, on_progress: Callable[[str, int, int], None]) -> Path:
    """Apply every action in `run.plan`, write the manifest, and return its path."""
    stamp = _stamp()
    manifest_path = paths.manifest_path(run.claude_dir)
    previous = record.load(manifest_path)
    manifest = record.new(run, stamp, previous=previous)
    total = len(run.plan)
    try:
        for completed, action in enumerate(run.plan, start=1):
            _apply_action(run, action, stamp, manifest)
            on_progress(str(action.target), completed, total)
    except OSError as exc:
        print(f"six-laws-kit: install error: {exc}", file=sys.stderr)  # noqa: T201
        manifest["entries"] = record.dedupe_entries(manifest["entries"])
        record.write(manifest, manifest_path)
        raise
    manifest["entries"] = record.dedupe_entries(manifest["entries"])
    record.write(manifest, manifest_path)
    return manifest_path


def _apply_action(run: Run, action: Action, stamp: str, manifest: dict) -> None:
    if action.kind == "create_file":
        _apply_create_file(action, manifest)
    elif action.kind == "copy_hook_file":
        _apply_copy_hook_file(action, manifest)
    elif action.kind == "append_line":
        _apply_append_line(run, action, stamp, manifest)
    elif action.kind == "insert_block":
        _apply_insert_block(run, action, stamp, manifest)
    elif action.kind == "merge_hooks":
        _apply_merge_hooks(run, action, stamp, manifest)


def _apply_create_file(action: Action, manifest: dict) -> None:
    if action.existed:
        return
    _write_atomic(action.target, action.payload, manifest)
    record.add_entry(manifest, _created_file_entry(action.target))


def _apply_copy_hook_file(action: Action, manifest: dict) -> None:
    _write_atomic(action.target, action.payload, manifest)
    if os.name != "nt":
        os.chmod(action.target, 0o755)
    record.add_entry(manifest, _created_file_entry(action.target))


def _apply_append_line(run: Run, action: Action, stamp: str, manifest: dict) -> None:
    if not action.existed:
        _write_atomic(action.target, action.payload, manifest)
        record.add_entry(manifest, _created_file_entry(action.target))
        return
    backup_entry = _make_backup(run, action.target, stamp, record_entry=True)
    _write_atomic(action.target, action.payload, manifest)
    if backup_entry is not None:
        backup_entry["sha256_after"] = record.sha256(action.target)
        record.add_entry(manifest, backup_entry)


def _apply_insert_block(run: Run, action: Action, stamp: str, manifest: dict) -> None:
    if not action.diff:
        return
    existing_text = action.existing_text or ""
    _make_backup(run, action.target, stamp, record_entry=False)
    sha_before = _sha256_text(existing_text)
    _write_atomic(action.target, action.payload, manifest)
    leading_blank_added, trailing_newline_added = _insert_flags(existing_text)
    record.add_entry(
        manifest,
        {
            "kind": "inserted_block",
            "path": str(action.target),
            "marker_id": action.marker_id,
            "marker_version": MARKER_VERSION,
            "begin": blocks.BEGIN.format(id=action.marker_id, v=MARKER_VERSION),
            "end": blocks.END.format(id=action.marker_id),
            "sha256_before": sha_before,
            "sha256_after": record.sha256(action.target),
            "bytes_added": len(action.payload.encode("utf-8")) - len(existing_text.encode("utf-8")),
            "leading_blank_added": leading_blank_added,
            "trailing_newline_added": trailing_newline_added,
        },
    )


def _insert_flags(existing_text: str) -> tuple[bool, bool]:
    _new_text, leading_blank_added, trailing_newline_added = blocks.insert(existing_text, "")
    return leading_blank_added, trailing_newline_added


def _apply_merge_hooks(run: Run, action: Action, stamp: str, manifest: dict) -> None:
    if not action.diff:
        return
    _make_backup(run, action.target, stamp, record_entry=False)
    additions = json.loads(action.payload)
    before = settings.load(action.target)
    before_text = json.dumps(before, indent=2) + "\n" if before else "{}\n"
    after, added = settings.merge_hooks(before, additions)
    after_text = json.dumps(after, indent=2) + "\n"
    _write_atomic(action.target, after_text, manifest)
    record.add_entry(
        manifest,
        {
            "kind": "settings_hooks",
            "path": str(action.target),
            "sha256_before": _sha256_text(before_text),
            "sha256_after": record.sha256(action.target),
            "added": added,
        },
    )


def _created_file_entry(target: Path) -> dict:
    return {
        "kind": "created_file",
        "path": str(target),
        "sha256_after": record.sha256(target),
        "bytes": target.stat().st_size,
    }


def _make_backup(run: Run, target: Path, stamp: str, *, record_entry: bool) -> dict | None:
    if not target.exists():
        return None
    rel = _relative_path(target, run.root)
    backup_path = paths.backups_dir(run.claude_dir, stamp) / rel
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup_path)
    if not record_entry:
        return None
    return {
        "kind": "backup",
        "path": str(target),
        "backup_path": str(backup_path),
        "sha256_before": record.sha256(target),
    }


def _relative_path(target: Path, base: Path) -> Path:
    try:
        return target.relative_to(base)
    except ValueError:
        parts = target.parts
        return Path(*parts[1:]) if target.is_absolute() and len(parts) > 1 else target


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_atomic(target: Path, text: str, manifest: dict) -> None:
    _ensure_dir_tracked(target.parent, manifest)
    tmp = target.with_name(target.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(tmp, target)


def _ensure_dir_tracked(directory: Path, manifest: dict) -> None:
    """Create `directory` (and any missing parent) one level at a time, recording a
    `created_dir` entry for every directory that did not already exist, so uninstall can remove
    exactly those again, deepest first, when empty.
    """
    if directory.exists() or directory == directory.parent:
        return
    _ensure_dir_tracked(directory.parent, manifest)
    if not directory.exists():
        directory.mkdir()
        record.add_entry(manifest, {"kind": "created_dir", "path": str(directory)})


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
