"""`run(run)` prints what the manifest under `run.claude_dir` says is installed, cross-checked
against what is still on disk; `report()` builds that text so tests and the wizard can both use it.
"""

from __future__ import annotations

from pathlib import Path

from six_laws_kit import paths
from six_laws_kit.manifest import record
from six_laws_kit.run_state import Run


def run(run: Run) -> int:
    """Print the status report for `run.claude_dir` and return 0."""
    manifest = record.load(paths.manifest_path(run.claude_dir))
    print(report(manifest, run.claude_dir), end="")  # noqa: T201
    return 0


def report(manifest: dict | None, claude_dir: Path) -> str:
    """Return the human-readable status text for `manifest` (or `None` if nothing is installed)."""
    if manifest is None:
        return f"six-laws-kit: not installed under {claude_dir}\n"
    lines = [
        f"six-laws-kit {manifest.get('kit_version', '?')} installed {manifest.get('installed_at', '?')}",
        f"modules: {', '.join(manifest.get('modules', []))}",
        "",
        "entries:",
    ]
    lines.extend(_entry_line(entry) for entry in manifest.get("entries", []))
    lines.append("")
    lines.append("heads:")
    lines.append(_head_summary_line(manifest.get("heads", [])))
    lines.extend(_head_line(head) for head in manifest.get("heads", []))
    return "\n".join(lines) + "\n"


def _head_summary_line(heads: list[dict]) -> str:
    self_count = sum(1 for head in heads if head.get("written_by") == "self")
    installer_count = sum(1 for head in heads if head.get("written_by") == "installer")
    return f"  self: {self_count}  installer: {installer_count}"


def _head_line(head: dict) -> str:
    return f"  {head.get('path')}: {head.get('written_by')} ({head.get('status')})"


def _entry_line(entry: dict) -> str:
    return f"  {entry.get('kind', '?')}: {entry.get('path', '?')} {_match_note(entry)}"


def _match_note(entry: dict) -> str:
    path_str = entry.get("path")
    if not path_str:
        return ""
    path = Path(path_str)
    if not path.exists():
        return "(missing)"
    expected = entry.get("sha256_after", entry.get("sha256_before"))
    if not expected:
        return ""
    try:
        current = record.sha256(path)
    except OSError:
        return "(unreadable)"
    return "(unchanged)" if current == expected else "(modified)"
