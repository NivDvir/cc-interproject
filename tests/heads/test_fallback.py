"""Tests for six_laws_kit.heads.fallback: the installer's own summary of a project's CLAUDE.md."""

from __future__ import annotations

from pathlib import Path

from six_laws_kit.heads import fallback

FOREST = Path(__file__).resolve().parents[2] / "fixtures" / "forest"


def test_row_from_claude_md_with_heading():
    row = fallback.row_from_claude_md(FOREST / "alpha" / "CLAUDE.md", 1.5, "timeout")
    assert row.name == "Meridian Logbook"
    assert row.owns.startswith("Meridian Logbook is a small tool")
    assert len(row.owns.split()) <= fallback.MAX_OWNS_WORDS
    assert row.asks_others_to_watch_for == "NOT STATED"
    assert row.contact_subject == "NOT STATED"
    assert row.written_by == "installer"
    assert row.status == "timeout"
    assert row.seconds == 1.5


def test_row_from_claude_md_without_heading(tmp_path):
    claude_md = tmp_path / "CLAUDE.md"
    claude_md.write_text(
        "This project has no heading at all, only a plain opening paragraph that describes it.\n"
    )
    row = fallback.row_from_claude_md(claude_md, 0.0, "error")
    assert row.name == tmp_path.name
    assert row.owns.startswith("This project has no heading")
    assert row.written_by == "installer"
    assert row.status == "error"


def test_row_from_claude_md_owns_cut_to_forty_words(tmp_path):
    claude_md = tmp_path / "CLAUDE.md"
    long_paragraph = " ".join(f"word{i}" for i in range(60))
    claude_md.write_text(f"# Wordy Project\n\n{long_paragraph}\n")
    row = fallback.row_from_claude_md(claude_md, 0.0, "fallback")
    assert row.name == "Wordy Project"
    assert len(row.owns.split()) == fallback.MAX_OWNS_WORDS
    assert row.owns.split()[0] == "word0"


def test_row_from_claude_md_missing_file(tmp_path):
    missing = tmp_path / "missing" / "CLAUDE.md"
    row = fallback.row_from_claude_md(missing, 0.0, "error")
    assert row.name == "missing"
    assert "NOT STATED" in row.owns
    assert row.written_by == "installer"
