"""Bug: installing twice appends a second copy of the whole registry table.

`write/plan.py:73` creates `PROJECT_REGISTRY.md` as a plain file with no kit markers on the first
install. On the second install the file exists, `blocks.contains` finds no marker, and
`write/plan.py:78` wraps a freshly rendered table in a marker block and appends it, so the file
ends up holding every project twice. Every other target in the plan is idempotent; this one is not.
"""

from __future__ import annotations

from pathlib import Path

from six_laws_kit.run_state import Run, Tree
from six_laws_kit.write import plan


def _run(tmp_path: Path) -> Run:
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    claude_md = project / "CLAUDE.md"
    claude_md.write_text("# Project\n\nOne paragraph about it.\n", encoding="utf-8")
    tree = Tree(path=project, name="Project", claude_md=claude_md, selected=True)
    return Run(
        mode="install",
        home=tmp_path,
        claude_dir=tmp_path / ".claude",
        root=tmp_path,
        no_browser=True,
        trees=[tree],
    )


def test_second_plan_leaves_the_registry_alone(tmp_path: Path) -> None:
    run = _run(tmp_path)
    first = next(a for a in plan.build(run) if a.target.name == "PROJECT_REGISTRY.md")
    first.target.parent.mkdir(parents=True, exist_ok=True)
    first.target.write_text(first.payload, encoding="utf-8")

    second = next(a for a in plan.build(_run(tmp_path)) if a.target.name == "PROJECT_REGISTRY.md")
    assert second.diff == "", "a second install appends a duplicate registry table"
