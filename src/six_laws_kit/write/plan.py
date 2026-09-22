"""`build(run)` walks the modules a `Run` wants installed and produces the ordered list of
`Action`s the Review step shows and `apply.execute` performs. Pure: reads disk to see what already
exists, writes nothing, computes every diff in memory. `render_text` prints the plan for
`--dry-run` and the terminal UI.
"""

from __future__ import annotations

import difflib
import importlib.resources
import json
from pathlib import Path

from six_laws_kit import paths
from six_laws_kit.run_state import Action, Run, Tree, selected_trees
from six_laws_kit.texts import loader
from six_laws_kit.write import blocks, registry, settings

LAW_FILES = ("SIX_LAWS.md", "INTERPROJECT_PROTOCOL.md", "PRIOR_ART.md", "DISPATCHER_QUEUE.md")
HOOK_SCRIPTS = ("packet_reminder.py", "labor_tally.py", "load_cap.py")
REGISTRY_MARKER = "registry"
POINTER_MARKER = "project-pointer"
MARKER_VERSION = 1


def build(run: Run) -> list[Action]:
    """Compute the full install plan for `run` and also store it on `run.plan`."""
    actions: list[Action] = []
    actions.extend(_law_file_actions(run))
    actions.append(_registry_action(run))
    account_action = _account_pointer_action(run)
    if account_action is not None:
        actions.append(account_action)
    actions.extend(_project_pointer_actions(run))
    if "routing" in run.modules:
        actions.extend(_routing_actions(run))
    run.plan = actions
    return actions


def render_text(actions: list[Action]) -> str:
    """Render `actions` as readable text: one line for a kept-existing file, or a header line
    plus unified diff for anything that changes.
    """
    lines: list[str] = []
    for action in actions:
        if action.kind == "create_file" and action.existed:
            lines.append(f"kept existing: {action.target}")
            continue
        if not action.diff:
            lines.append(f"{action.kind}: {action.target} (no change)")
            continue
        lines.append(f"{action.kind}: {action.target}")
        lines.append(action.diff)
    return "\n".join(lines) + ("\n" if lines else "")


def _law_file_actions(run: Run) -> list[Action]:
    actions = []
    for name in LAW_FILES:
        target = run.claude_dir / name
        if target.exists():
            actions.append(_kept_existing_action(target))
        else:
            actions.append(_create_file_action(target, loader.read(name)))
    return actions


def _registry_action(run: Run) -> Action:
    """Plan `PROJECT_REGISTRY.md`: wrapped in the "registry" marker block from its very first
    creation, so a re-install can find and refresh it (`blocks.replace_block`) instead of
    appending a second copy of the table underneath a fresh, unrelated block.
    """
    target = run.claude_dir / "PROJECT_REGISTRY.md"
    header = loader.read("REGISTRY_HEADER.md")
    body = registry.render(run.rows, run.trees, header)
    if not target.exists():
        return _create_file_action(target, blocks.render(REGISTRY_MARKER, MARKER_VERSION, body))
    existing_text = _read_existing(target)
    if not blocks.contains(existing_text, REGISTRY_MARKER):
        block = _block_for(REGISTRY_MARKER, body, existing_text)
        new_text, _leading, _trailing = blocks.insert(existing_text, block)
        return _insert_block_action(target, REGISTRY_MARKER, existing_text, new_text)
    new_text, replaced = blocks.replace_block(existing_text, REGISTRY_MARKER, MARKER_VERSION, body)
    if not replaced:
        return _unchanged_block_action(target, REGISTRY_MARKER, existing_text)
    return _insert_block_action(target, REGISTRY_MARKER, existing_text, new_text)


def _account_pointer_action(run: Run) -> Action | None:
    part_a = loader.read("ACCOUNT_POINTER.md").split("\n\n---")[0].strip()
    target = run.claude_dir / "CLAUDE.md"
    existed = target.exists()
    existing_text = _read_existing(target) if existed else ""
    if part_a in existing_text:
        return None
    new_text = _append_line(existing_text, part_a)
    diff = _unified_diff(existing_text, new_text, target)
    return Action(
        kind="append_line",
        target=target,
        marker_id=None,
        payload=new_text,
        existing_text=existing_text if existed else None,
        diff=diff,
        existed=existed,
    )


def _project_pointer_actions(run: Run) -> list[Action]:
    body = loader.read("PROJECT_POINTER.md")
    actions = []
    for tree in selected_trees(run):
        action = _pointer_action_for_tree(tree, body)
        if action is not None:
            actions.append(action)
    return actions


def _pointer_action_for_tree(tree: Tree, body: str) -> Action | None:
    target = tree.claude_md
    existed = target.exists()
    existing_text = _read_existing(target) if existed else ""
    if blocks.contains(existing_text, POINTER_MARKER):
        return None
    block = _block_for(POINTER_MARKER, body, existing_text)
    new_text, _leading, _trailing = blocks.insert(existing_text, block)
    diff = _unified_diff(existing_text, new_text, target)
    return Action(
        kind="insert_block",
        target=target,
        marker_id=POINTER_MARKER,
        payload=new_text,
        existing_text=existing_text if existed else None,
        diff=diff,
        existed=existed,
    )


def _routing_actions(run: Run) -> list[Action]:
    hooks_dir = paths.hooks_dir(run.claude_dir)
    actions = [_copy_hook_action(hooks_dir / name, _read_hook_source(name)) for name in HOOK_SCRIPTS]
    actions.append(_copy_hook_action(hooks_dir / "PACKET_REMINDER.md", loader.read("PACKET_REMINDER.md")))
    actions.append(_settings_action(run))
    return actions


def _settings_action(run: Run) -> Action:
    target = run.claude_dir / "settings.json"
    additions = settings.hook_additions(paths.hook_interpreter(), paths.hooks_dir(run.claude_dir))
    before_text, after_text = settings.preview(target, additions)
    diff = _unified_diff(before_text, after_text, target)
    return Action(
        kind="merge_hooks",
        target=target,
        marker_id=None,
        payload=json.dumps(additions),
        existing_text=before_text if target.exists() else None,
        diff=diff,
        existed=target.exists(),
    )


def _read_hook_source(filename: str) -> str:
    """Read one of the kit's standalone hook programs. Uses `importlib.resources` (like
    `texts.loader.read`) rather than `Path(__file__)`, since the latter raises when the package
    is running from inside the zipapp bundle.
    """
    resource = importlib.resources.files("six_laws_kit.hooks").joinpath(filename)
    return resource.read_text(encoding="utf-8")


def _copy_hook_action(target: Path, payload: str) -> Action:
    existed = target.exists()
    existing_text = _read_existing(target) if existed else None
    diff = _unified_diff(existing_text or "", payload, target)
    return Action(
        kind="copy_hook_file",
        target=target,
        marker_id=None,
        payload=payload,
        existing_text=existing_text,
        diff=diff,
        existed=existed,
    )


def _kept_existing_action(target: Path) -> Action:
    return Action(
        kind="create_file",
        target=target,
        marker_id=None,
        payload="",
        existing_text=None,
        diff="",
        existed=True,
    )


def _create_file_action(target: Path, payload: str) -> Action:
    diff = _unified_diff("", payload, target)
    return Action(
        kind="create_file",
        target=target,
        marker_id=None,
        payload=payload,
        existing_text=None,
        diff=diff,
        existed=False,
    )


def _unchanged_block_action(target: Path, marker_id: str, existing_text: str) -> Action:
    return Action(
        kind="insert_block",
        target=target,
        marker_id=marker_id,
        payload=existing_text,
        existing_text=existing_text,
        diff="",
        existed=True,
    )


def _insert_block_action(target: Path, marker_id: str, existing_text: str, new_text: str) -> Action:
    diff = _unified_diff(existing_text, new_text, target)
    return Action(
        kind="insert_block",
        target=target,
        marker_id=marker_id,
        payload=new_text,
        existing_text=existing_text,
        diff=diff,
        existed=True,
    )


def _append_line(existing: str, line: str) -> str:
    if not existing:
        return line + "\n"
    newline = "\r\n" if existing.endswith("\r\n") else "\n"
    text = existing if existing.endswith(("\n", "\r\n")) else existing + newline
    if not text.endswith(("\n\n", "\r\n\r\n")):
        text += newline
    return text + line + "\n"


def _read_existing(target: Path) -> str:
    """Read a pre-existing file's exact text: `newline=""` disables universal-newline
    translation, so a CRLF-authored file (and any BOM, since `encoding="utf-8"` never strips one)
    round-trips byte-for-byte instead of being silently rewritten as LF.
    """
    return target.read_text(encoding="utf-8", newline="")


def _block_for(marker_id: str, body: str, existing_text: str) -> str:
    """Render a marker block whose own begin/end/body line endings match `existing_text`'s, so
    appending it to a CRLF file does not leave the file with mixed line endings.
    """
    block = blocks.render(marker_id, MARKER_VERSION, body)
    if "\r\n" in existing_text:
        block = block.replace("\r\n", "\n").replace("\n", "\r\n")
    return block


def _unified_diff(before: str, after: str, target: Path) -> str:
    if before == after:
        return ""
    before_lines = before.splitlines(keepends=True)
    after_lines = after.splitlines(keepends=True)
    diff = difflib.unified_diff(before_lines, after_lines, fromfile=str(target), tofile=str(target))
    return "".join(diff)
