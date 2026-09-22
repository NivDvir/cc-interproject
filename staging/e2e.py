"""Drive the bundled installer end to end against a staging HOME built by `build_home.py`, using
only the fake `claude` in `fixtures/claude_fake`. Seven steps run in order (build, dry run,
install, status, re-install, uninstall, tree shape); each prints PASS or FAIL with a one-line
reason. `pytest tests/staging` imports this module and calls the same step functions.

Usage: `python3 staging/e2e.py --home DIR [--keep]`. Exit codes: 0 every step passed, 1 otherwise.
"""

# ruff: noqa: T201

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

STAGING_DIR = Path(__file__).resolve().parent
REPO_ROOT = STAGING_DIR.parent
FAKE_CLAUDE_DIR = REPO_ROOT / "fixtures" / "claude_fake"
TEXTS_DIR = REPO_ROOT / "src" / "cc_interproject" / "texts"
BACKUPS_PREFIX = ".claude/interproject-backups/"

ACCOUNT_FILES = (
    "INTERPROJECT_LAWS.md",
    "INTERPROJECT_PROTOCOL.md",
    "PRIOR_ART.md",
    "DISPATCHER_QUEUE.md",
    "PROJECT_REGISTRY.md",
    "interproject.manifest.json",
)
LEGACY_TAIL = "## Notes added after that block"


def _load_sibling(name: str):
    spec = importlib.util.spec_from_file_location(f"staging_{name}", STAGING_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_home = _load_sibling("build_home")
tree_shape = _load_sibling("tree_shape")
EXPECTED_PROJECTS = build_home.EXPECTED_PROJECTS
POINTER_BEGIN, POINTER_END = build_home.POINTER_BEGIN, build_home.POINTER_END


def account_pointer_line() -> str:
    """Part (a) of `texts/ACCOUNT_POINTER.md`: the single line the install appends."""
    return (TEXTS_DIR / "ACCOUNT_POINTER.md").read_text(encoding="utf-8").split("\n\n---")[0].strip()


def installer_path(holder: list) -> tuple[Path, str]:
    """`dist/install.py` when `tools/bundle.py --check` says it is current, else a freshly built
    bundle in a temporary directory (this harness never writes into `dist/`).
    """
    check = subprocess.run(
        [sys.executable, "tools/bundle.py", "--check"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    if check.returncode == 0:
        return REPO_ROOT / "dist" / "install.py", "dist/install.py (current)"
    tmp = tempfile.mkdtemp(prefix="cc-interproject-bundle-")
    holder.append(tmp)
    subprocess.run(
        [sys.executable, "tools/bundle.py", "--output-dir", tmp],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(tmp) / "install.py", "freshly built bundle (dist/install.py was stale)"


def kit_env(home: Path) -> dict:
    """The process environment every installer call runs under: fake `claude` first on PATH."""
    env = dict(os.environ)
    env["PATH"] = f"{FAKE_CLAUDE_DIR}{os.pathsep}{env.get('PATH', '')}"
    env["HOME"] = str(home)
    env["KIT_FAKE_MODE"] = "ok"
    env["KIT_SKIP_AUTH"] = "1"
    env.pop("CLAUDE_CONFIG_DIR", None)
    return env


def run_installer(
    installer: Path, home: Path, args: list[str], stdin_text: str
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(installer), *args],
        cwd=str(REPO_ROOT),
        env=kit_env(home),
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=600,
    )


def snapshot(home: Path) -> dict:
    """sha256 of every file under `home`, keyed by relative posix path. Symlinks are recorded by
    their target and never followed, so the linked project is hashed once.
    """
    digests: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(home, followlinks=False):
        here = Path(dirpath)
        for name in list(dirnames):
            entry = here / name
            if entry.is_symlink():
                dirnames.remove(name)
                digests[entry.relative_to(home).as_posix()] = f"symlink:{os.readlink(entry)}"
        for name in filenames:
            entry = here / name
            key = entry.relative_to(home).as_posix()
            if entry.is_symlink():
                digests[key] = f"symlink:{os.readlink(entry)}"
            else:
                digests[key] = hashlib.sha256(entry.read_bytes()).hexdigest()
    return digests


def compare(before: dict, after: dict, ignore_prefix: str | None = None) -> list[str]:
    """Return a readable list of differences between two snapshots, ignoring one path prefix."""

    def keep(key: str) -> bool:
        return ignore_prefix is None or not key.startswith(ignore_prefix)

    before_keys = {k for k in before if keep(k)}
    after_keys = {k for k in after if keep(k)}
    problems = [f"added {k}" for k in sorted(after_keys - before_keys)]
    problems += [f"removed {k}" for k in sorted(before_keys - after_keys)]
    problems += [f"changed {k}" for k in sorted(before_keys & after_keys) if before[k] != after[k]]
    return problems


def registry_rows(text: str, home: Path) -> list[list[str]]:
    """Every seven-column registry row in `text` whose Path cell is under `home`."""
    rows = []
    for line in text.splitlines():
        stripped = line.lstrip("+").strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        if len(cells) == 7 and cells[1].startswith(str(home) + os.sep):
            rows.append(cells)
    return rows


def _expected_paths(home: Path) -> set:
    return {str(home / relative) for relative in EXPECTED_PROJECTS}


def step1_build(home: Path) -> tuple[bool, str, dict]:
    """Build the staging HOME and take the pre-install snapshot."""
    build_home.build(home)
    before = snapshot(home)
    missing = [rel for rel in EXPECTED_PROJECTS if not (home / rel / "CLAUDE.md").exists()]
    if missing:
        return False, f"builder did not place {missing}", before
    return True, f"{len(before)} files, {len(EXPECTED_PROJECTS)} projects planted", before


def step2_dry_run(installer: Path, home: Path, before: dict) -> tuple[bool, str]:
    """`--dry-run` must discover exactly the expected projects and write nothing."""
    proc = run_installer(installer, home, ["--dry-run", "--no-browser", "--root", str(home)], "all\n")
    if proc.returncode != 0:
        return False, f"exit {proc.returncode}: {proc.stderr.strip()[-200:]}"
    found = {row[1] for row in registry_rows(proc.stdout, home)}
    expected = _expected_paths(home)
    if found != expected:
        extra = sorted(p.replace(str(home) + os.sep, "") for p in found - expected)
        missing = sorted(p.replace(str(home) + os.sep, "") for p in expected - found)
        return False, f"discovered set wrong; extra={extra} missing={missing}"
    drift = compare(before, snapshot(home))
    if drift:
        return False, f"dry run touched the disk: {drift[:3]}"
    return True, f"{len(found)} projects discovered, nothing written"


def step3_install(installer: Path, home: Path) -> tuple[bool, str]:
    """The real install, then every content check the plan promises."""
    proc = run_installer(installer, home, ["--no-browser", "--root", str(home)], "all\ny\n")
    if proc.returncode != 0:
        return False, f"exit {proc.returncode}: {proc.stderr.strip()[-200:]}"
    checks = (
        _check_account_files,
        _check_account_claude_md,
        _check_settings_untouched,
        _check_registry,
        _check_blocks,
        _check_encoding_and_language,
        _check_manifest,
    )
    problems = [reason for check in checks for ok, reason in [check(home)] if not ok]
    if problems:
        return False, f"{len(problems)} problem(s): " + "; ".join(problems)
    return True, f"{len(EXPECTED_PROJECTS) - 1} blocks, settings.json kept, registry all self"


def _check_account_files(home: Path) -> tuple[bool, str]:
    missing = [name for name in ACCOUNT_FILES if not (home / ".claude" / name).is_file()]
    return (not missing), f"missing under .claude: {missing}" if missing else ""


def _check_account_claude_md(home: Path) -> tuple[bool, str]:
    original = build_home.template("claude_global.md")
    text = (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    line = account_pointer_line()
    if not text.startswith(original):
        return False, ".claude/CLAUDE.md no longer starts with the user's own instructions"
    if text.count(line) != 1:
        return False, f".claude/CLAUDE.md has {text.count(line)} pointer lines, expected 1"
    if text[len(original) :].strip() != line:
        return False, ".claude/CLAUDE.md gained more than the one pointer line"
    return True, ""


def _check_settings_untouched(home: Path) -> tuple[bool, str]:
    """The installer must leave `.claude/settings.json` exactly as the builder wrote it, byte for
    byte — the user's own model, env, permissions and their own registered commands alike.
    """
    expected = build_home.settings_bytes()
    current = (home / ".claude" / "settings.json").read_bytes()
    if current != expected:
        return False, f".claude/settings.json changed: {len(expected)} bytes -> {len(current)}"
    return True, ""


def _check_registry(home: Path) -> tuple[bool, str]:
    text = (home / ".claude" / "PROJECT_REGISTRY.md").read_text(encoding="utf-8")
    rows = registry_rows(text, home)
    paths = [row[1] for row in rows]
    if sorted(paths) != sorted(_expected_paths(home)):
        return False, f"registry has {len(paths)} rows, expected {len(EXPECTED_PROJECTS)}"
    not_self = [row[1] for row in rows if row[5] != "self"]
    if not_self:
        return False, f"registry rows not written-by self: {not_self}"
    for relative in ("code/api", "code/dotfiles"):
        if str(home / relative) not in paths:
            return False, f"registry is missing {relative}"
    return True, ""


def _check_blocks(home: Path) -> tuple[bool, str]:
    for relative in EXPECTED_PROJECTS:
        path = home / relative / "CLAUDE.md"
        text = path.read_text(encoding="utf-8")
        if text.count(POINTER_BEGIN) != 1 or text.count(POINTER_END) != 1:
            return False, f"{relative}: {text.count(POINTER_BEGIN)} kit blocks, expected 1"
        if relative == "code/legacy":
            if LEGACY_TAIL not in text.split(POINTER_END)[1]:
                return False, "code/legacy lost the text that followed its existing block"
        elif not text.rstrip("\r\n").endswith(POINTER_END):
            return False, f"{relative}: the kit block is not at the end of the file"
    return True, ""


def _check_encoding_and_language(home: Path) -> tuple[bool, str]:
    raw = (home / "code/ml-lab/CLAUDE.md").read_bytes()
    if not raw.startswith(b"\xef\xbb\xbf"):
        return False, "code/ml-lab lost its UTF-8 BOM"
    head = raw.split(POINTER_BEGIN.encode("utf-8"))[0]
    if head.replace(b"\r\n", b"").count(b"\n"):
        return False, "code/ml-lab gained bare LF line endings outside the block"
    french = build_home.template("acme_claude_fr.md")
    acme = (home / "Projects/Client Work/acme site/CLAUDE.md").read_text(encoding="utf-8")
    if not acme.startswith(french):
        return False, "the French CLAUDE.md was altered"
    return True, ""


def _check_manifest(home: Path) -> tuple[bool, str]:
    manifest = json.loads((home / ".claude" / "interproject.manifest.json").read_text(encoding="utf-8"))
    entries = manifest.get("entries", [])
    created = {entry["path"] for entry in entries if entry["kind"] == "created_file"}
    expected_created = {str(home / ".claude" / name) for name in ACCOUNT_FILES if "manifest" not in name}
    if not expected_created <= created:
        return False, f"manifest is missing created_file entries: {sorted(expected_created - created)}"
    blocks = [entry for entry in entries if entry["kind"] == "inserted_block"]
    wanted = len(EXPECTED_PROJECTS) - 1  # every project but `code/legacy`, which has one already
    if len(blocks) != wanted:
        return False, f"manifest records {len(blocks)} inserted blocks, expected {wanted}"
    if not any(entry["kind"] == "backup" for entry in entries):
        return False, "manifest has no backup entry for the account CLAUDE.md"
    if len(manifest.get("heads", [])) != len(EXPECTED_PROJECTS):
        return False, f"manifest heads: {len(manifest.get('heads', []))} of {len(EXPECTED_PROJECTS)}"
    return True, ""


def step4_status(installer: Path, home: Path) -> tuple[bool, str]:
    """`--status` must exit 0 and name every registered project."""
    proc = run_installer(installer, home, ["--status", "--root", str(home)], "")
    if proc.returncode != 0:
        return False, f"exit {proc.returncode}: {proc.stderr.strip()[-200:]}"
    missing = [rel for rel in EXPECTED_PROJECTS if str(home / rel) not in proc.stdout]
    if missing:
        return False, f"--status did not list {missing}"
    return True, f"{len(EXPECTED_PROJECTS)} head rows listed"


def step5_idempotence(installer: Path, home: Path) -> tuple[bool, str]:
    """A second identical install must change nothing that the first one wrote."""
    registry_before = (home / ".claude" / "PROJECT_REGISTRY.md").read_text(encoding="utf-8")
    proc = run_installer(installer, home, ["--no-browser", "--root", str(home)], "all\ny\n")
    if proc.returncode != 0:
        return False, f"exit {proc.returncode}: {proc.stderr.strip()[-200:]}"
    ok, reason = _check_blocks(home)
    if not ok:
        return False, f"re-install duplicated a block: {reason}"
    ok, reason = _check_settings_untouched(home)
    if not ok:
        return False, f"re-install touched settings.json: {reason}"
    registry_after = (home / ".claude" / "PROJECT_REGISTRY.md").read_text(encoding="utf-8")
    rows_before, rows_after = registry_rows(registry_before, home), registry_rows(registry_after, home)
    if rows_after != rows_before:
        return False, f"registry rows changed: {len(rows_before)} -> {len(rows_after)}"
    return True, "no duplicated blocks or registry rows"


def step6_uninstall(installer: Path, home: Path, before: dict) -> tuple[bool, str]:
    """`--uninstall` must return every file to its step-1 bytes and leave no empty kit directory."""
    proc = run_installer(installer, home, ["--uninstall", "--root", str(home)], "")
    if proc.returncode != 0:
        return False, f"exit {proc.returncode}: {proc.stderr.strip()[-200:]}"
    drift = compare(before, snapshot(home), ignore_prefix=BACKUPS_PREFIX)
    if drift:
        return False, f"{len(drift)} files differ from the pre-install snapshot, e.g. {drift[:4]}"
    return True, "every file restored, no kit directories left"


def run_all(home: Path, installer: Path) -> list:
    """Run all seven steps in order and return `[(name, ok, reason)]`."""
    results = []
    ok, reason, before = step1_build(home)
    results.append(("1 build staging HOME", ok, reason))
    steps = (
        ("2 dry run discovers every tree", lambda: step2_dry_run(installer, home, before)),
        ("3 install writes the plan", lambda: step3_install(installer, home)),
        ("4 --status lists every row", lambda: step4_status(installer, home)),
        ("5 re-install is idempotent", lambda: step5_idempotence(installer, home)),
        ("6 --uninstall restores all", lambda: step6_uninstall(installer, home, before)),
        ("7 trees nest to any depth", lambda: tree_shape.step7_tree_shape(installer, home)),
    )
    for name, call in steps:
        step_ok, step_reason = call()
        results.append((name, step_ok, step_reason))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="End-to-end run of the installer on a staging HOME.")
    parser.add_argument("--home", required=True, metavar="DIR", help="Where to build the staging HOME.")
    parser.add_argument("--keep", action="store_true", help="Do not remove the staging HOME at the end.")
    args = parser.parse_args(argv)

    home = Path(args.home).expanduser()
    if home.exists() and any(home.iterdir()):
        print(f"e2e.py: {home} exists and is not empty; refusing", file=sys.stderr)
        return 2
    temp_dirs: list = []
    installer, note = installer_path(temp_dirs)
    print(f"e2e.py: installer = {note}")
    print(f"e2e.py: home      = {home}")
    started = time.time()
    try:
        results = run_all(home, installer)
    finally:
        for temp in temp_dirs:
            shutil.rmtree(temp, ignore_errors=True)
    width = max(len(name) for name, _ok, _reason in results)
    print()
    for name, ok, reason in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {reason}")
    failed = [name for name, ok, _reason in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} steps passed in {time.time() - started:.1f}s")
    if failed:
        print("failed: " + ", ".join(failed))
    _cleanup(home, keep=args.keep)
    return 1 if failed else 0


def _cleanup(home: Path, keep: bool) -> None:
    """Remove the staging HOME only when this run built it (the builder's marker file says so)."""
    if keep:
        print(f"kept: {home}")
        return
    if (home / build_home.MARKER_NAME).is_file():
        shutil.rmtree(home, ignore_errors=True)
    else:
        print(f"e2e.py: no {build_home.MARKER_NAME} marker in {home}; leaving it alone", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
