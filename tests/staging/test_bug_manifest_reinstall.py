"""Bug: a second install replaces the manifest, so `--uninstall` can no longer undo the first one.

`write/apply.py:28` starts every run from `manifest.record.new(...)`, an empty `entries` list, and
overwrites `~/.claude/interproject.manifest.json` at the end. On a re-install the idempotent steps
record nothing (`write/apply.py:_apply_create_file` returns early when the file already exists,
`_apply_insert_block` returns early when its diff is empty), so the new manifest forgets the law
files, the pointer blocks and the account pointer
line. A later `--uninstall` then leaves all of them on disk.
"""

from __future__ import annotations

import json
from pathlib import Path

from cc_interproject import paths
from cc_interproject.run_state import Run, Tree
from cc_interproject.write import apply, plan


def _run(tmp_path: Path) -> Run:
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    claude_md = project / "CLAUDE.md"
    if not claude_md.exists():
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


def _install(tmp_path: Path) -> dict:
    run = _run(tmp_path)
    plan.build(run)
    manifest_path = apply.execute(run, lambda _target, _done, _total: None)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def test_reinstall_keeps_the_first_installs_entries(tmp_path: Path) -> None:
    first = _install(tmp_path)
    second = _install(tmp_path)

    first_paths = {entry["path"] for entry in first["entries"]}
    second_paths = {entry["path"] for entry in second["entries"]}
    forgotten = sorted(first_paths - second_paths)
    assert not forgotten, f"the re-install's manifest can no longer undo: {forgotten}"
    assert paths.manifest_path(tmp_path / ".claude").exists()
