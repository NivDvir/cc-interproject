from __future__ import annotations

import hashlib
from pathlib import Path

from six_laws_kit.manifest import record
from six_laws_kit.run_state import Row, Run


def _run(tmp_path: Path) -> Run:
    run = Run(
        mode="install", home=tmp_path, claude_dir=tmp_path / "dot-claude", root=tmp_path, no_browser=True
    )
    run.rows = {
        "/home/alpha": Row(
            name="Alpha",
            owns="x",
            asks_others_to_watch_for="y",
            contact_subject="z",
            written_by="self",
            status="ok",
            seconds=1.2,
        )
    }
    return run


def test_new_builds_the_documented_header_fields(tmp_path: Path):
    manifest = record.new(_run(tmp_path), "20260101T000000Z")
    assert manifest["schema"] == 1
    assert manifest["kit_name"] == "six-laws-kit"
    assert manifest["installed_at"] == "20260101T000000Z"
    assert manifest["entries"] == []
    assert manifest["heads"] == [
        {"path": "/home/alpha", "written_by": "self", "status": "ok", "seconds": 1.2}
    ]
    assert manifest["backup_dir"].endswith("20260101T000000Z")


def test_add_entry_appends_in_place():
    manifest = {"entries": []}
    record.add_entry(manifest, {"kind": "created_file", "path": "x"})
    assert manifest["entries"] == [{"kind": "created_file", "path": "x"}]


def test_write_then_load_round_trips(tmp_path: Path):
    manifest = {"schema": 1, "entries": [{"kind": "created_file", "path": "x"}]}
    path = tmp_path / "six-laws.manifest.json"
    record.write(manifest, path)
    assert path.read_text(encoding="utf-8").endswith("\n")
    assert record.load(path) == manifest


def test_load_missing_file_returns_none(tmp_path: Path):
    assert record.load(tmp_path / "nope.json") is None


def test_load_malformed_json_returns_none(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    assert record.load(path) is None


def test_sha256_matches_hashlib(tmp_path: Path):
    # write_bytes, not write_text: text mode applies universal-newline translation on write, so
    # "\n" becomes "\r\n" on Windows and the file would no longer be the exact bytes hashed below.
    path = tmp_path / "f.txt"
    path.write_bytes(b"hello\n")
    assert record.sha256(path) == hashlib.sha256(b"hello\n").hexdigest()
