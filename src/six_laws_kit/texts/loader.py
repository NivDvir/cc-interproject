"""Read the kit's static public-text files (SIX_LAWS.md, PRIOR_ART.md, and the rest).

Works both from the source tree and from inside a zipapp, where this package lives in an
in-memory zip and `Path(__file__)` does not point at a real file. `read` goes through
`paths.read_package_resource` (`pkgutil.get_data`), not `importlib.resources.files(...).joinpath`,
which can mis-join separators on a Windows zipimport. `names` still uses `importlib.resources`
with a `Path` fallback, since directory listing (not single-file reads) is not affected.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

from six_laws_kit import paths

_SKIP = {"__init__.py", "loader.py", "ARCHITECTURE.md"}


def read(name: str) -> str:
    """Return the text of one file this package ships, e.g. "SIX_LAWS.md"."""
    return paths.read_package_resource(__package__, name)


def names() -> list[str]:
    """Return the names of every text file this package ships, sorted."""
    try:
        entries = importlib.resources.files(__package__).iterdir()
        found = [entry.name for entry in entries if entry.is_file() and entry.name not in _SKIP]
    except (FileNotFoundError, NotADirectoryError, AttributeError):
        found = [p.name for p in Path(__file__).parent.iterdir() if p.is_file() and p.name not in _SKIP]
    return sorted(found)
