"""Build a registry row directly from a project's own CLAUDE.md, for when the headless `claude -p`
head call could not answer for it (docs/DESIGN.md section 4). This is the installer's own
best-effort summary, never the project's own answer, so every row this module produces is
`written_by="installer"`.
"""

from __future__ import annotations

from pathlib import Path

from cc_interproject.run_state import Row

MAX_OWNS_WORDS = 40


def row_from_claude_md(claude_md: Path, seconds: float, status: str) -> Row:
    """Read `claude_md` and build an installer-written fallback Row for it."""
    text = _read_text(claude_md)
    name = _extract_name(text, claude_md)
    owns = _extract_owns(text, name)
    return Row(
        name=name,
        owns=owns,
        asks_others_to_watch_for="NOT STATED",
        contact_subject="NOT STATED",
        written_by="installer",
        status=status,
        seconds=round(seconds, 2),
    )


def _read_text(claude_md: Path) -> str:
    try:
        return claude_md.read_text(encoding="utf-8")
    except OSError:
        return ""


def _extract_name(text: str, claude_md: Path) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            heading = line[2:].strip()
            if heading:
                return heading
    return claude_md.parent.name


def _extract_owns(text: str, name: str) -> str:
    paragraph = _first_paragraph(text)
    if not paragraph:
        return f"NOT STATED (no CLAUDE.md content found for {name})"
    words = paragraph.split()
    if len(words) > MAX_OWNS_WORDS:
        paragraph = " ".join(words[:MAX_OWNS_WORDS])
    return paragraph


def _first_paragraph(text: str) -> str:
    """The first run of non-blank, non-heading lines, wherever it starts."""
    paragraph_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("# "):
            continue
        if line.strip() == "":
            if paragraph_lines:
                break
            continue
        paragraph_lines.append(line.strip())
    return " ".join(paragraph_lines)
