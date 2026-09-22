"""The `<!-- six-laws-kit:begin/end -->` marker convention used to make a piece of installed text
findable and removable again. `render` builds one block; `contains` detects one; `insert` appends
one to the end of a file's text; `strip` removes one back out. All four tolerate CRLF line endings.
"""

from __future__ import annotations

import re

BEGIN = "<!-- six-laws-kit:begin id={id} v={v} -->"
END = "<!-- six-laws-kit:end id={id} -->"

_BLANK_LINE_RE = re.compile(r"(\r?\n)(\r?\n)\Z")
_NEWLINE_RE = re.compile(r"\r?\n\Z")


def render(marker_id: str, version: int, body: str) -> str:
    """Return one complete marker block: begin line, body, end line, each newline-terminated."""
    body_text = body if body.endswith(("\n", "\r\n")) else body + "\n"
    begin_line = BEGIN.format(id=marker_id, v=version)
    end_line = END.format(id=marker_id)
    return f"{begin_line}\n{body_text}{end_line}\n"


def contains(text: str, marker_id: str) -> bool:
    """True if a begin marker for `marker_id` (any version) is present anywhere in `text`."""
    pattern = re.compile(r"<!-- six-laws-kit:begin id=" + re.escape(marker_id) + r" v=\d+ -->")
    return pattern.search(text) is not None


def insert(text: str, block: str) -> tuple[str, bool, bool]:
    """Append `block` (as returned by `render`) to `text`.

    Ensures the existing text ends with a newline before appending (adding one if it does not),
    then ensures it ends with a full blank line (adding a second newline if it does not already).
    Returns `(new_text, leading_blank_added, trailing_newline_added)`.
    """
    leading_blank_added = False
    trailing_newline_added = False
    working = text
    if working:
        newline = "\r\n" if working.endswith("\r\n") else "\n"
        if _NEWLINE_RE.search(working) is None:
            working += newline
            trailing_newline_added = True
        if _BLANK_LINE_RE.search(working) is None:
            working += newline
            leading_blank_added = True
    new_text = working + block
    if _NEWLINE_RE.search(new_text) is None:
        new_text += "\n"
    return new_text, leading_blank_added, trailing_newline_added


def strip(text: str, marker_id: str) -> tuple[str, bool]:
    """Remove the marker block for `marker_id`, inclusive, and the blank line `insert` would have
    added directly before it. Returns `(new_text, found_exactly_once)`; `text` is returned
    unchanged when the marker is absent or present more than once.
    """
    pattern = re.compile(
        r"<!-- six-laws-kit:begin id="
        + re.escape(marker_id)
        + r" v=\d+ -->\r?\n"
        + r".*?"
        + r"<!-- six-laws-kit:end id="
        + re.escape(marker_id)
        + r" -->",
        re.DOTALL,
    )
    matches = list(pattern.finditer(text))
    if len(matches) != 1:
        return text, False
    match = matches[0]
    start, end = match.start(), match.end()
    blank = _BLANK_LINE_RE.search(text[:start])
    if blank:
        start = blank.start(2)
    if text[end : end + 2] == "\r\n":
        end += 2
    elif text[end : end + 1] == "\n":
        end += 1
    return text[:start] + text[end:], True
