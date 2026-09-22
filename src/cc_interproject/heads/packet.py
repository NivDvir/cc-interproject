"""The exact prompt sent to a project's own `claude -p` head call, the JSON Schema its answer must
satisfy, and the command line that sends it. See `docs/DESIGN.md` section 4.
"""

from __future__ import annotations

import json

PACKET = """Read your own CLAUDE.md. Read nothing outside this directory: no other files, no other
projects, no web or tool calls beyond reading that one file.

Describe THIS project for a shared registry that every other Claude Code project on this machine
can read. Answer with exactly four fields, each at most 40 words:

- name: this project's name.
- owns: what this project owns and is responsible for.
- asks_others_to_watch_for: what this project wants other projects to notice and report back to
  it, if anything.
- contact_subject: the subject line another project should use when it needs to reach this one.

Invent nothing. If a field has no true answer, write exactly "NOT STATED" for that field.
Do not describe any other project, even one you know about from context.

Return only the JSON object:
{"name": "...", "owns": "...", "asks_others_to_watch_for": "...", "contact_subject": "..."}"""

ROW_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "maxLength": 120},
        "owns": {"type": "string", "maxLength": 400},
        "asks_others_to_watch_for": {"type": "string", "maxLength": 400},
        "contact_subject": {"type": "string", "maxLength": 200},
    },
    "required": ["name", "owns", "asks_others_to_watch_for", "contact_subject"],
    "additionalProperties": False,
}


def build_command(claude_bin: str, json_schema: bool) -> list[str]:
    """The head-call command line for one project, per DESIGN.md section 4."""
    command = [
        claude_bin,
        "-p",
        "--model",
        "sonnet",
        "--allowedTools",
        "Read",
        "Glob",
        "--disallowedTools",
        "Write",
        "Edit",
        "Bash",
        "WebFetch",
        "--output-format",
        "json",
    ]
    if json_schema:
        command += ["--json-schema", json.dumps(ROW_SCHEMA)]
    command += ["--max-turns", "6", "--max-budget-usd", "0.25"]
    return command
