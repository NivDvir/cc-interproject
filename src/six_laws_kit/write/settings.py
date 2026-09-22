"""Loads, previews, and idempotently merges the kit's three hook entries into a
`~/.claude/settings.json`-shaped dict, and removes them again on uninstall. Never touches disk
directly (that is `apply.py`'s job) except for `load`, which reads one existing file.
"""

from __future__ import annotations

import copy
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path

from six_laws_kit import paths

_SAME_PURPOSE_NEEDLES = (
    "packet-wrap",
    "labor-tally",
    "load-cap",
    "packet_reminder",
    "labor_tally",
    "load_cap",
)


def load(path: Path) -> dict:
    """Return the parsed JSON object at `path`, or `{}` if the file is missing or unreadable."""
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"six-laws-kit: could not read {path}: {exc}", file=sys.stderr)  # noqa: T201
        return {}
    return data if isinstance(data, dict) else {}


def hook_additions(interpreter: list[str], hooks_dir: Path) -> list[dict]:
    """Return the kit's three hook registrations, ready to pass to `merge_hooks`."""
    return [
        {
            "event": "UserPromptSubmit",
            "matcher": None,
            "command": paths.hook_command(interpreter, hooks_dir / "packet_reminder.py"),
            "timeout": 10,
        },
        {
            "event": "Stop",
            "matcher": None,
            "command": paths.hook_command(interpreter, hooks_dir / "labor_tally.py"),
            "timeout": 20,
        },
        {
            "event": "PreToolUse",
            "matcher": "Agent|Task|SendMessage|Read|Grep|Glob|Bash|WebFetch",
            "command": paths.hook_command(interpreter, hooks_dir / "load_cap.py"),
            "timeout": 5,
        },
    ]


def merge_hooks(settings: dict, additions: list[dict]) -> tuple[dict, list[dict]]:
    """Merge `additions` into a copy of `settings`, idempotently.

    An addition is skipped if its exact command already appears anywhere in `settings`. Otherwise
    it is appended to the first group of its event whose matcher equals its own, or to a new group
    when none matches. Key order is preserved throughout. Returns `(new_settings, actually_added)`.
    """
    new_settings = copy.deepcopy(settings)
    hooks = new_settings.setdefault("hooks", {})
    existing_commands = set(_all_commands(new_settings))
    added: list[dict] = []
    for addition in additions:
        if addition["command"] in existing_commands:
            continue
        group = _find_or_create_group(hooks, addition)
        group["hooks"].append(
            {"type": "command", "command": addition["command"], "timeout": addition["timeout"]}
        )
        existing_commands.add(addition["command"])
        added.append(addition)
    return new_settings, added


def _find_or_create_group(hooks: dict, addition: dict) -> dict:
    event_groups = hooks.setdefault(addition["event"], [])
    for group in event_groups:
        if group.get("matcher") == addition["matcher"]:
            return group
    group = {"matcher": addition["matcher"], "hooks": []}
    event_groups.append(group)
    return group


def remove_hooks(settings: dict, commands: list[str]) -> dict:
    """Return a copy of `settings` with any hook dict whose `command` is in `commands` dropped,
    along with any group or event list that becomes empty as a result.
    """
    new_settings = copy.deepcopy(settings)
    hooks = new_settings.get("hooks", {})
    command_set = set(commands)
    for event in list(hooks.keys()):
        remaining_groups = []
        for group in hooks[event]:
            remaining_hooks = [h for h in group.get("hooks", []) if h.get("command") not in command_set]
            if remaining_hooks:
                group["hooks"] = remaining_hooks
                remaining_groups.append(group)
        if remaining_groups:
            hooks[event] = remaining_groups
        else:
            del hooks[event]
    return new_settings


def same_purpose_hooks(settings: dict) -> list[str]:
    """Return every command already registered whose script basename looks like one of the
    owner's own tally/cap hooks or this kit's own hooks (a reinstall guard).
    """
    return [command for command in _all_commands(settings) if _looks_same_purpose(command)]


def _looks_same_purpose(command: str) -> bool:
    basename = _basename_from_command(command)
    return any(needle in basename for needle in _SAME_PURPOSE_NEEDLES)


def _basename_from_command(command: str) -> str:
    match = re.search(r'"([^"]+)"', command)
    token = match.group(1) if match else (command.split()[-1] if command.split() else command)
    return token.replace("\\", "/").rsplit("/", 1)[-1]


def _all_commands(settings: dict) -> Iterator[str]:
    for groups in settings.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("command")
                if command:
                    yield command


def preview(path: Path, additions: list[dict]) -> tuple[str, str]:
    """Return `(before_text, after_text)`: the JSON text of `path` today, and after `additions`
    would be merged into it. Used to build the settings.json unified diff.
    """
    before = load(path)
    before_text = json.dumps(before, indent=2) + "\n" if before else "{}\n"
    after, _added = merge_hooks(before, additions)
    after_text = json.dumps(after, indent=2) + "\n"
    return before_text, after_text
