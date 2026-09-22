"""Builds the single-file installer: zips `src/cc_interproject/` into `dist/install.py` with
`zipapp`, plus a `dist/SHA256SUMS` next to it. `--check` rebuilds into a temp directory and exits
1 if the result differs from what is committed, so CI catches a stale bundle.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tempfile
import time
import zipapp
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_PACKAGE = REPO_ROOT / "src" / "cc_interproject"
ARCHIVE_NAME = "install.py"
SUMS_NAME = "SHA256SUMS"
FIXED_TIMESTAMP = 946684800  # 2000-01-01T00:00:00Z: safe above the 1980 ZIP floor in any timezone
_FILE_MODE = 0o644
_DIR_MODE = 0o755
_MSDOS_DIR_ATTR = 0x10
_UNIX_CREATE_SYSTEM = 3
SKIP_NAMES = {"__pycache__", "ARCHITECTURE.md"}
SKIP_SUFFIXES = {".pyc"}


def stage_source(staging_dir: Path) -> None:
    """Copy `src/cc_interproject` into `staging_dir`, excluding caches, bytecode, and ARCHITECTURE.md,
    then freeze every file's mtime so repeated builds hash identically.
    """

    def _ignore(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name in SKIP_NAMES or Path(name).suffix in SKIP_SUFFIXES}

    shutil.copytree(SOURCE_PACKAGE, staging_dir / "cc_interproject", ignore=_ignore)
    for path in staging_dir.rglob("*"):
        os.utime(path, (FIXED_TIMESTAMP, FIXED_TIMESTAMP))


def build(output_dir: Path) -> Path:
    """Build `install.py` and `SHA256SUMS` into `output_dir`; return the archive path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / ARCHIVE_NAME
    with tempfile.TemporaryDirectory() as staging:
        stage_source(Path(staging))
        zipapp.create_archive(
            source=Path(staging),
            target=archive_path,
            interpreter="/usr/bin/env python3",
            main="cc_interproject.cli:main",
            # Uncompressed (ZIP_STORED): DEFLATE output is not guaranteed byte-identical across
            # zlib builds/versions, which would make the committed archive's hash depend on which
            # machine built it. Stored bytes are copied verbatim, so the archive hashes the same
            # on every OS and Python build, which --check (and the committed dist/install.py)
            # depend on.
            compressed=False,
        )
    _normalize_archive_timestamps(archive_path)
    (output_dir / SUMS_NAME).write_text(f"{_sha256(archive_path)}  {ARCHIVE_NAME}\n", encoding="utf-8")
    return archive_path


def _normalize_archive_timestamps(archive_path: Path) -> None:
    """Rewrite every zip member's stored date-time to `FIXED_TIMESTAMP`.

    `zipapp.create_archive` writes its generated `__main__.py` with `ZipFile.writestr`, which
    stamps that one entry with the current wall-clock time instead of a source file's (already
    fixed) mtime. Left alone, that one entry makes the archive's hash differ between any two
    builds, defeating both `--check` and a reproducible commit of `dist/install.py`.
    """
    # gmtime, not localtime: the archive must hash the same regardless of the *building*
    # machine's own timezone (this repo's dev machine is UTC+2/+3; GitHub-hosted runners are
    # UTC), so the epoch constant is interpreted as UTC wall-clock time everywhere.
    date_time = time.gmtime(FIXED_TIMESTAMP)[:6]
    shebang_len = len(b"#!/usr/bin/env python3\n")
    prefix = archive_path.read_bytes()[:shebang_len]
    with zipfile.ZipFile(archive_path) as source:
        entries = [(info, source.read(info)) for info in source.infolist()]
    # Sort by filename: zipapp's own member order comes from `Path.rglob`, which (like plain
    # `os.scandir`) is free to return entries in whatever order the OS/filesystem hands them
    # back, not necessarily sorted and not necessarily the same across two runs or two hosts.
    # A fixed member order, on top of the fixed timestamp below, is what makes the final byte
    # layout - and hence the sha256 --check compares - independent of the machine that built it.
    entries.sort(key=lambda pair: pair[0].filename)
    mode = archive_path.stat().st_mode
    with tempfile.NamedTemporaryFile(dir=archive_path.parent, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(prefix)
    with zipfile.ZipFile(tmp_path, "a", compression=zipfile.ZIP_STORED) as target:
        for info, data in entries:
            info.date_time = date_time
            # `external_attr` and `create_system` otherwise carry the *building* host's own
            # stat().st_mode and OS id (whatever git checkout / umask produced there), which is
            # exactly the kind of per-machine noise this normalize pass exists to remove. Every
            # bundled file is plain, non-executable source; only the outer archive itself needs
            # its own exec bit, handled separately below.
            is_dir = info.filename.endswith("/")
            unix_mode = _DIR_MODE if is_dir else _FILE_MODE
            info.external_attr = (unix_mode << 16) | (_MSDOS_DIR_ATTR if is_dir else 0)
            info.create_system = _UNIX_CREATE_SYSTEM
            target.writestr(info, data)
    tmp_path.replace(archive_path)
    archive_path.chmod(mode)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(output_dir: Path) -> bool:
    """Rebuild into a temp directory and compare its sha256 against `output_dir`'s recorded one."""
    recorded = output_dir / SUMS_NAME
    if not recorded.exists():
        print(f"tools/bundle.py: {recorded} missing; run without --check first", file=sys.stderr)
        return False
    expected = recorded.read_text(encoding="utf-8").split()[0]
    with tempfile.TemporaryDirectory() as tmp:
        actual = _sha256(build(Path(tmp)))
    if actual != expected:
        print(f"tools/bundle.py: dist/install.py is stale ({actual} != {expected})", file=sys.stderr)
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the cc-interproject zipapp installer.")
    parser.add_argument("--check", action="store_true", help="Verify the build is current; write nothing.")
    parser.add_argument("--output-dir", default="dist", metavar="DIR", help="Where to write the archive.")
    args = parser.parse_args(argv)
    output_dir = Path(args.output_dir)
    if args.check:
        return 0 if check(output_dir) else 1
    archive_path = build(output_dir)
    print(f"tools/bundle.py: wrote {archive_path} ({archive_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
