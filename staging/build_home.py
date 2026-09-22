"""Build a throwaway HOME directory that looks like a real Claude Code user's machine, so the
installer can be exercised against something messier than `fixtures/forest`. Content comes from
the files in `staging/templates/`; this module only places them and generates the session
transcripts. Nothing here reads or imports `src/six_laws_kit`.

Usage: `python3 staging/build_home.py --out DIR`. Exit codes: 0 ok, 2 DIR exists and is not empty.
"""

# ruff: noqa: T201

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent / "templates"
MARKER_NAME = ".six-laws-staging"
SEED = 20260922

# The marker text `write/blocks.py` renders for a project pointer. Hard-coded on purpose: the
# staging home must not import the code under test. `tests/staging` asserts it still matches.
POINTER_BEGIN = "<!-- six-laws-kit:begin id=project-pointer v=1 -->"
POINTER_END = "<!-- six-laws-kit:end id=project-pointer -->"

# HOME-relative posix paths of every project the scan is expected to discover, in no order.
EXPECTED_PROJECTS = (
    "code/webapp",
    "code/api",
    "code/monorepo",
    "code/monorepo/packages/ui",
    "code/monorepo/packages/core",
    "Documents/thesis",
    "code/ml-lab",
    "code/dotfiles",
    "Projects/Client Work/acme site",
    "code/legacy",
    "code/archive/old-app.backup-2025-01-01",
    "code/swift-tool",
)

# CLAUDE.md files that exist but must never be discovered.
DECOY_PROJECTS = (
    "code/webapp/node_modules/@scope/design-tokens",
    "code/api/.venv/lib/python3.12/site-packages/x",
    "code/monorepo/packages/core/.claude/worktrees/feat-x",
    "code/swift-tool/.build/checkouts/dep",
    "code/deep/a/b/c/d/e/f/g/project",
)

# Projects that already have session transcripts under `.claude/projects/`.
SESSION_PROJECTS = (
    "code/webapp",
    "code/api",
    "code/monorepo",
    "Documents/thesis",
    "code/ml-lab",
    "Projects/Client Work/acme site",
)

TOOL_CALLS = (
    ("Read", {"file_path": "src/index.ts"}, "1\timport { render } from './app'\n"),
    ("Bash", {"command": "npm test"}, "Test Files  12 passed (12)\n"),
    ("Grep", {"pattern": "TODO", "path": "src"}, "src/lib/api.ts:44:  // TODO: retry\n"),
    ("Glob", {"pattern": "**/*.test.ts"}, "src/lib/api.test.ts\nsrc/routes/cart.test.ts\n"),
    ("Edit", {"file_path": "src/lib/api.ts"}, "Applied 1 edit.\n"),
)

USER_TURNS = (
    "Why is the cart total wrong when a coupon is applied twice?",
    "Add a test for the empty state and run the suite.",
    "The build got 40 kB bigger since Friday. Find out why.",
    "Can you summarise what changed in this file last week?",
    "Rename this helper and update every caller.",
)

ASSISTANT_TURNS = (
    "Looking at the coupon path first.",
    "The suite passes. One snapshot needed updating.",
    "The growth is a new icon set imported at the top level.",
    "Two commits touched it, both small refactors.",
    "Done. Nine call sites updated, tests still green.",
)


def template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def settings_bytes() -> bytes:
    """The exact bytes `_dot_claude` writes to `.claude/settings.json`. `e2e.py` compares the
    installed tree against this to prove the installer never rewrote the user's own file.
    """
    return (json.dumps(json.loads(template("settings.json")), indent=2) + "\n").encode("utf-8")


def write_text(path: Path, text: str, *, crlf: bool = False, bom: bool = False) -> None:
    """Write `text` to `path`, creating parents. `crlf` and `bom` model a Windows-authored file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = text.replace("\n", "\r\n") if crlf else text
    data = body.encode("utf-8")
    path.write_bytes(b"\xef\xbb\xbf" + data if bom else data)


def encode_project_dir(home: Path, relative: str) -> str:
    """The `~/.claude/projects` directory name Claude Code writes for a project path."""
    return re.sub(r"[^A-Za-z0-9-]", "-", (home / relative).as_posix())


def build(out: Path) -> Path:
    """Create the whole staging HOME under `out` and return it."""
    rng = random.Random(SEED)
    out.mkdir(parents=True, exist_ok=True)
    _projects(out)
    _decoys(out)
    _dot_claude(out, rng)
    _junk(out)
    (out / MARKER_NAME).write_text(
        json.dumps({"built_by": "staging/build_home.py", "at": _now().isoformat()}) + "\n",
        encoding="utf-8",
    )
    return out


def _projects(home: Path) -> None:
    write_text(home / "code/webapp/CLAUDE.md", template("webapp_claude.md"))
    write_text(home / "code/webapp/package.json", template("package.json"))
    _fake_git(home / "code/webapp")
    _node_modules(home / "code/webapp")

    write_text(home / "code/api/CLAUDE.md", template("api_claude.md"))
    write_text(home / "code/api/pyproject.toml", template("pyproject.toml"))
    write_text(home / "code/api/app/main.py", "from fastapi import FastAPI\n\napp = FastAPI()\n")

    write_text(home / "code/monorepo/CLAUDE.md", template("monorepo_root.md"))
    write_text(home / "code/monorepo/packages/ui/CLAUDE.md", template("monorepo_ui.md"))
    write_text(home / "code/monorepo/packages/core/CLAUDE.md", template("monorepo_core.md"))

    write_text(home / "Documents/thesis/CLAUDE.md", template("thesis_claude.md"))
    write_text(home / "Documents/thesis/main.tex", "\\documentclass{book}\n\\begin{document}\n")

    write_text(home / "code/ml-lab/CLAUDE.md", template("ml_lab_claude.md"), crlf=True, bom=True)

    write_text(home / "code/dotfiles/CLAUDE.md", "")
    write_text(home / "code/dotfiles/zshrc", "export EDITOR=vim\n")

    write_text(home / "Projects/Client Work/acme site/CLAUDE.md", template("acme_claude_fr.md"))
    write_text(home / "code/legacy/CLAUDE.md", template("legacy_claude.md"))
    write_text(home / "code/archive/old-app.backup-2025-01-01/CLAUDE.md", template("archive_claude.md"))
    write_text(home / "code/swift-tool/CLAUDE.md", template("swift_tool_claude.md"))
    write_text(home / "code/swift-tool/Package.swift", "// swift-tools-version:5.9\n")

    os.symlink("webapp", home / "code/link-to-webapp", target_is_directory=True)


def _decoys(home: Path) -> None:
    for relative in DECOY_PROJECTS:
        name = "deep_claude.md" if relative.startswith("code/deep/") else "vendored_claude.md"
        write_text(home / relative / "CLAUDE.md", template(name))


def _fake_git(project: Path) -> None:
    write_text(project / ".git/HEAD", "ref: refs/heads/main\n")
    write_text(project / ".git/config", "[core]\n\trepositoryformatversion = 0\n")
    write_text(project / ".git/refs/heads/main", "0" * 40 + "\n")


def _node_modules(project: Path) -> None:
    for package in ("react", "vite", "@scope/design-tokens"):
        manifest = json.dumps({"name": package, "version": "1.0.0"}, indent=2) + "\n"
        write_text(project / "node_modules" / package / "package.json", manifest)


def _dot_claude(home: Path, rng: random.Random) -> None:
    claude = home / ".claude"
    write_text(claude / "CLAUDE.md", template("claude_global.md"))
    settings = json.loads(template("settings.json"))
    write_text(claude / "settings.json", json.dumps(settings, indent=2) + "\n")
    write_text(claude / "my-hooks/format-on-write.sh", "#!/bin/bash\nexit 0\n")
    write_text(claude / "my-hooks/prompt-log.sh", "#!/bin/bash\nexit 0\n")
    write_text(claude / "plugins/notes-helper/.claude-plugin/plugin.json", template("plugin.json"))
    write_text(
        claude / "plugins/notes-helper/commands/note.md",
        "---\ndescription: Start a note\n---\n\nStart a note about $ARGUMENTS.\n",
    )
    for junk_dir, junk_file, body in (
        ("statsig", "statsig.cached.evaluations.1", '{"values":{}}\n'),
        ("todos", "4d1c9a2f-agent.json", "[]\n"),
        ("shell-snapshots", "snapshot-zsh-1758000000.sh", "# zsh snapshot\n"),
    ):
        write_text(claude / junk_dir / junk_file, body)
    _sessions(home, claude, rng)


def _sessions(home: Path, claude: Path, rng: random.Random) -> None:
    today_index = rng.randrange(len(SESSION_PROJECTS))
    for index, relative in enumerate(SESSION_PROJECTS):
        session_dir = claude / "projects" / encode_project_dir(home, relative)
        entries = []
        for number in range(rng.randint(1, 3)):
            days_ago = 0 if (index == today_index and number == 0) else rng.randint(1, 89)
            entries.append(_one_transcript(home / relative, session_dir, days_ago, rng))
        write_text(
            session_dir / "sessions-index.json",
            json.dumps({"version": 1, "sessions": entries}, indent=2) + "\n",
        )


def _one_transcript(cwd: Path, session_dir: Path, days_ago: int, rng: random.Random) -> dict:
    session_id = str(uuid.UUID(int=rng.getrandbits(128), version=4))
    started = _now() - timedelta(days=days_ago, hours=rng.randint(0, 6))
    lines, last = _transcript_lines(cwd, session_id, started, rng)
    path = session_dir / f"{session_id}.jsonl"
    write_text(path, "".join(lines))
    os.utime(path, (last.timestamp(), last.timestamp()))
    return {
        "sessionId": session_id,
        "startedAt": started.isoformat(),
        "lastActiveAt": last.isoformat(),
        "messageCount": len(lines),
        "summary": rng.choice(USER_TURNS)[:60],
    }


def _transcript_lines(
    cwd: Path, session_id: str, started: datetime, rng: random.Random
) -> tuple[list[str], datetime]:
    lines: list[str] = []
    stamp = started
    target = rng.randint(20, 60)
    common = {"sessionId": session_id, "cwd": str(cwd), "version": "2.1.268", "isSidechain": False}

    def add(role: str, content: list, gap: int) -> None:
        nonlocal stamp
        stamp += timedelta(seconds=rng.randint(1, gap))
        record = dict(common, type=role, uuid=str(uuid.UUID(int=rng.getrandbits(128), version=4)))
        record["timestamp"] = stamp.isoformat().replace("+00:00", "Z")
        record["message"] = {"role": role, "content": content}
        lines.append(json.dumps(record) + "\n")

    while len(lines) < target:
        add("user", [{"type": "text", "text": rng.choice(USER_TURNS)}], 240)
        for _ in range(rng.randint(1, 3)):
            tool, tool_input, tool_result = rng.choice(TOOL_CALLS)
            call_id = f"toolu_{rng.getrandbits(48):012x}"
            add("assistant", [{"type": "tool_use", "id": call_id, "name": tool, "input": tool_input}], 30)
            add("user", [{"type": "tool_result", "tool_use_id": call_id, "content": tool_result}], 20)
        add("assistant", [{"type": "text", "text": rng.choice(ASSISTANT_TURNS)}], 40)
    return lines, stamp


def _junk(home: Path) -> None:
    account = {
        "numStartups": 214,
        "installMethod": "native",
        "theme": "dark",
        "projects": {str(home / rel): {"allowedTools": []} for rel in SESSION_PROJECTS},
    }
    write_text(home / ".claude.json", json.dumps(account, indent=2) + "\n")
    write_text(home / "Library/Application Support/SomeApp/state.plist", "<plist></plist>\n")
    write_text(home / "Library/Caches/com.example.tool/cache.db", "not-a-real-database\n")
    write_text(home / ".Trash/old-notes/CLAUDE.md", template("vendored_claude.md"))
    write_text(home / ".Trash/old-notes/scratch.txt", "deleted on purpose\n")
    write_text(home / "Downloads/installer-2.4.1.dmg", "binary-ish\n")
    write_text(home / "Downloads/report.pdf", "%PDF-1.4\n")


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a staging HOME for the six-laws-kit tests.")
    parser.add_argument("--out", required=True, metavar="DIR", help="Where to build the HOME.")
    args = parser.parse_args(argv)
    out = Path(args.out).expanduser()
    if out.exists() and any(out.iterdir()):
        print(f"build_home.py: {out} exists and is not empty; refusing", file=sys.stderr)
        return 2
    build(out)
    print(f"build_home.py: built staging HOME at {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
