"""Ask every selected project's own `claude -p` head call for its registry row, in parallel, in
the background. See `docs/DESIGN.md` section 4 for the parse tiers and `docs/INTERFACES.md` for
the signatures this module must expose.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from six_laws_kit.heads import fallback, packet
from six_laws_kit.run_state import Row, Run, Tree, selected_trees

AUTH_FAILURE_MARKERS = (
    "not logged in",
    "please run /login",
    "invalid api key",
    "authentication",
)


def is_auth_failure_text(text: str) -> bool:
    """True if `text` reads as a local `claude` CLI login failure, never a head-side problem."""
    if not text:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in AUTH_FAILURE_MARKERS)


def parse_row(envelope_text: str) -> dict[str, str] | None:
    """Parse a head's answer through three tiers: `structured_output`, then `result` as JSON
    (fence stripped), then the first balanced `{...}` inside `result`. None if none apply."""
    envelope = _parse_json_object(envelope_text)
    if envelope is None:
        return None
    structured = envelope.get("structured_output")
    if isinstance(structured, dict):
        return structured
    result = envelope.get("result")
    if not isinstance(result, str):
        return None
    parsed = _parse_json_object(_strip_code_fence(result))
    if parsed is not None:
        return parsed
    balanced = _first_balanced_object(result)
    return _parse_json_object(balanced) if balanced is not None else None


def _parse_json_object(text: str | None) -> dict[str, object] | None:
    if not text:
        return None
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _first_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for index in range(start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _row_from_fields(fields: dict[str, object] | None, tree: Tree, elapsed: float) -> Row:
    if not isinstance(fields, dict):
        return fallback.row_from_claude_md(tree.claude_md, elapsed, "fallback")
    name = str(fields.get("name") or "").strip()
    owns = str(fields.get("owns") or "").strip()
    if not name or not owns:
        return fallback.row_from_claude_md(tree.claude_md, elapsed, "fallback")
    watch = str(fields.get("asks_others_to_watch_for") or "").strip() or "NOT STATED"
    contact = str(fields.get("contact_subject") or "").strip() or "NOT STATED"
    return Row(
        name=name,
        owns=owns,
        asks_others_to_watch_for=watch,
        contact_subject=contact,
        written_by="self",
        status="ok",
        seconds=round(elapsed, 2),
    )


def ask_one(claude_bin: str, tree: Tree, json_schema: bool, timeout: int) -> Row:
    """Blocking: run one head call for `tree` and return its Row (real or fallback)."""
    command = packet.build_command(claude_bin, json_schema)
    started = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=tree.path,
            input=packet.PACKET,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return fallback.row_from_claude_md(tree.claude_md, time.time() - started, "timeout")
    except OSError:
        return fallback.row_from_claude_md(tree.claude_md, time.time() - started, "error")

    elapsed = time.time() - started
    if proc.returncode != 0:
        combined = (proc.stdout or "") + (proc.stderr or "")
        status = "authfail" if is_auth_failure_text(combined) else "error"
        return fallback.row_from_claude_md(tree.claude_md, elapsed, status)

    fields = parse_row(proc.stdout or "")
    return _row_from_fields(fields, tree, elapsed)


def _progress_label(status: str) -> str:
    if status == "ok":
        return "answered"
    if status == "timeout":
        return "timeout"
    return "fallback"


def _ask_and_store(run: Run, tree: Tree, json_schema: bool, timeout: int) -> None:
    key = str(tree.path)
    with run.lock:
        run.ask_progress[key] = "asked"
    row = ask_one(run.claude_bin, tree, json_schema, timeout)
    with run.lock:
        run.rows[key] = row
        run.ask_progress[key] = _progress_label(row.status)


def _run_all(run: Run, max_workers: int, timeout: int) -> None:
    trees = selected_trees(run)
    json_schema = bool(run.claude_caps.get("json_schema"))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_ask_and_store, run, tree, json_schema, timeout): tree for tree in trees}
        for future in as_completed(futures):
            future.result()


def start(run: Run, max_workers: int = 4, timeout: int = 120) -> None:
    """Launch a background thread that asks every selected tree for its row, in parallel."""
    thread = threading.Thread(target=_run_all, args=(run, max_workers, timeout), daemon=True)
    thread.start()


def all_done(run: Run) -> bool:
    """True once every selected tree has a final progress state."""
    trees = selected_trees(run)
    with run.lock:
        progress = dict(run.ask_progress)
    final_states = ("answered", "fallback", "timeout")
    return all(progress.get(str(tree.path)) in final_states for tree in trees)
