"""Read the kit's static public-text files (SIX_LAWS.md, PRIOR_ART.md, and the rest).

Works both from the source tree and from inside a zipapp, where this package lives in an
in-memory zip and `Path(__file__)` does not point at a real file. `importlib.resources.files`
handles both cases on Python 3.9+; the `Path` fallback below only covers a resource backend that
cannot address a zipapp member directly.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

_SKIP = {"__init__.py", "loader.py", "ARCHITECTURE.md"}


def read(name: str) -> str:
    """Return the text of one file this package ships, e.g. "SIX_LAWS.md"."""
    try:
        resource = importlib.resources.files(__package__).joinpath(name)
        return resource.read_text(encoding="utf-8")
    except (FileNotFoundError, NotADirectoryError, AttributeError):
        return (Path(__file__).parent / name).read_text(encoding="utf-8")


def names() -> list[str]:
    """Return the names of every text file this package ships, sorted."""
    try:
        entries = importlib.resources.files(__package__).iterdir()
        found = [entry.name for entry in entries if entry.is_file() and entry.name not in _SKIP]
    except (FileNotFoundError, NotADirectoryError, AttributeError):
        found = [p.name for p in Path(__file__).parent.iterdir() if p.is_file() and p.name not in _SKIP]
    return sorted(found)
