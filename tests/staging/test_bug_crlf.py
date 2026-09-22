"""Bug: a CLAUDE.md written with CRLF line endings is rewritten with LF throughout.

`write/plan.py:116` reads the target with `Path.read_text(encoding="utf-8")`, which applies
universal-newline translation, so every `\\r\\n` is already `\\n` by the time
`write/blocks.insert` looks for one and `write/apply._write_atomic` writes the file back with
`newline="\\n"`. The CRLF detection in `write/blocks.py` can therefore never fire, the user sees
every line of the file as changed, and `--uninstall` cannot restore the original bytes.
"""

from __future__ import annotations

from pathlib import Path

from six_laws_kit.run_state import Run, Tree
from six_laws_kit.write import plan


def test_pointer_insert_keeps_crlf(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    claude_md = project / "CLAUDE.md"
    claude_md.write_bytes(b"# Project\r\n\r\nOne paragraph about it.\r\n")

    tree = Tree(path=project, name="Project", claude_md=claude_md, selected=True)
    run = Run(
        mode="install",
        home=tmp_path,
        claude_dir=tmp_path / ".claude",
        root=tmp_path,
        no_browser=True,
        trees=[tree],
    )
    actions = plan.build(run)
    pointer = next(action for action in actions if action.marker_id == plan.POINTER_MARKER)

    original_part = pointer.payload.split(plan.blocks.BEGIN.format(id=plan.POINTER_MARKER, v=1))[0]
    assert "\r\n" in original_part, "the project's own CRLF line endings were normalised to LF"
