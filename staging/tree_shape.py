"""Step 7 of the staging harness: read the staging forest back through the kit's own Scan step
and check that one tree really is one unit of unbounded depth. `code/platform` must come back
from `GET /api/state` as a single head with three levels of subtree nested under it, and
`wizard/terminal.py` must print all four of its names with each indented further than the one
above it. `e2e.py` loads this module the way it loads `build_home.py`; it is not imported.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

SCAN_TIMEOUT_SECONDS = 180
SCAN_POLL_SECONDS = 0.2
PLATFORM_ROOT = "code/platform"
PLATFORM_DESCENDANTS = ("services", "services/billing", "services/billing/ledger")

# The names the four `code/platform` CLAUDE.md files carry, head first.
PLATFORM_NAMES = ("Platform", "Platform Services", "Billing Service", "Billing Ledger")


def kit_modules(installer: Path):
    """Import the kit from the bundle under test, so the tree JSON and the terminal rendering
    checked here are the ones the shipped installer produces. Under `pytest tests/staging` the
    package is already imported from `src/`, which is the same code; leave that import alone.
    """
    if "six_laws_kit" not in sys.modules:
        sys.path.insert(0, str(installer))
    from six_laws_kit.run_state import Run
    from six_laws_kit.wizard import api, terminal

    return api, terminal, Run


def scan_trees(installer: Path, home: Path) -> list:
    """Run the wizard's own Scan step over `home` and return its nested tree JSON, exactly as
    `GET /api/state` hands it to the page.
    """
    api, _terminal, run_class = kit_modules(installer)
    run = run_class(mode="dry-run", home=home, claude_dir=home / ".claude", root=home, no_browser=True)
    api.scan_start(run)
    deadline = time.time() + SCAN_TIMEOUT_SECONDS
    while not api.scan_progress(run).get("done") and time.time() < deadline:
        time.sleep(SCAN_POLL_SECONDS)
    return api.state(run).get("trees") or []


def step7_tree_shape(installer: Path, home: Path) -> tuple[bool, str]:
    """Both checks, in order; the first failure names itself."""
    trees = scan_trees(installer, home)
    ok, reason = check_nesting(trees, home)
    if not ok:
        return False, reason
    _api, terminal, _run_class = kit_modules(installer)
    return check_indentation(terminal._render_forest(trees))


def check_nesting(trees: list, home: Path) -> tuple[bool, str]:
    """`code/platform` is one top-level tree holding a child, a grandchild and a leaf."""
    node = next((t for t in trees if t["path"] == str(home / PLATFORM_ROOT)), None)
    if node is None:
        return False, f"{PLATFORM_ROOT} is not a top-level tree"
    for relative in PLATFORM_DESCENDANTS:
        subtrees = node.get("subtrees") or []
        if len(subtrees) != 1:
            return False, f"{PLATFORM_ROOT}/{relative}: parent has {len(subtrees)} subtrees, expected 1"
        node = subtrees[0]
        if node["path"] != str(home / PLATFORM_ROOT / relative):
            return False, f"expected {PLATFORM_ROOT}/{relative}, got {node['path']}"
    if node.get("subtrees"):
        return False, "the great-grandchild should be a leaf"
    return True, ""


def check_indentation(lines: list) -> tuple[bool, str]:
    """Every name appears once in the terminal forest, each further right than the one above."""
    columns = []
    for name in PLATFORM_NAMES:
        needle = f"{name}  ("
        match = next((line for line in lines if needle in line), None)
        if match is None:
            return False, f"the terminal forest never printed {name!r}"
        columns.append(match.index(needle))
    if any(later <= earlier for earlier, later in zip(columns, columns[1:])):
        return False, f"terminal indentation does not increase with depth: {columns}"
    return True, f"3 levels nested, terminal indents at columns {columns}"
