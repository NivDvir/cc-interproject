"""Tests for tools/bundle.py: build the zipapp installer into a temp directory, then run it
exactly as a downloaded `install.py` would be run — version, status, dry-run, and reading its
bundled assets and texts through `importlib.resources` from inside the archive. `tools/` is a
build-time script outside the `cc_interproject` package, so it is loaded here by file path.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = REPO_ROOT / "fixtures"
RENDER_PAGE_CHECK = (
    "import sys; sys.path.insert(0, sys.argv[1]); "
    "from cc_interproject.wizard import server; "
    "html = server.render_page('t'); "
    "assert '<!--@css-->' not in html and 'KIT_TOKEN' in html; "
    "print('page ok', len(html))"
)


def _load_bundle():
    spec = importlib.util.spec_from_file_location("bundle_under_test", REPO_ROOT / "tools" / "bundle.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bundle = _load_bundle()


@pytest.fixture(scope="module")
def archive_path(tmp_path_factory) -> Path:
    return bundle.build(tmp_path_factory.mktemp("dist"))


def _env(home: Path) -> dict:
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["PATH"] = f"{FIXTURES_DIR / 'claude_fake'}{os.pathsep}{env.get('PATH', '')}"
    env["KIT_SKIP_AUTH"] = "1"
    env["KIT_FAKE_MODE"] = "ok"
    return env


def _run(archive: Path, args: list[str], home: Path, stdin: str = "") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(archive), *args],
        env=_env(home),
        input=stdin,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_version_prints_name_and_version(archive_path, tmp_path):
    result = _run(archive_path, ["--version"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "cc-interproject 0.1.0"


def test_status_under_temp_home_exits_0(archive_path, tmp_path):
    result = _run(archive_path, ["--status", "--root", str(tmp_path)], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "not installed" in result.stdout


def test_dry_run_against_forest_fixture_exits_0(archive_path, forest_home):
    result = _run(
        archive_path,
        ["--dry-run", "--no-browser", "--root", str(forest_home)],
        forest_home,
        stdin="all\n",
    )
    assert result.returncode == 0, result.stderr


def test_wizard_page_renders_from_inside_the_archive(archive_path):
    result = subprocess.run(
        [sys.executable, "-c", RENDER_PAGE_CHECK, str(archive_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "page ok" in result.stdout


def test_build_is_reproducible(tmp_path):
    first = bundle.build(tmp_path / "one")
    second = bundle.build(tmp_path / "two")
    assert first.read_bytes() == second.read_bytes()
    assert (tmp_path / "one" / "SHA256SUMS").read_text() == (tmp_path / "two" / "SHA256SUMS").read_text()


def test_empty_source_directory_does_not_change_archive_hash(tmp_path, monkeypatch):
    """A directory kept alive only by an ignored entry (a stray `__pycache__` under a package that
    was otherwise `git rm -r`'d) must not turn into an empty archive member: an empty directory has
    no file behind it, so letting it in would make the hash depend on directory survival rather
    than on source content, exactly the CI-only failure this regression guards against.
    """
    source_copy = tmp_path / "cc_interproject"
    shutil.copytree(bundle.SOURCE_PACKAGE, source_copy)
    monkeypatch.setattr(bundle, "SOURCE_PACKAGE", source_copy)

    baseline = bundle.build(tmp_path / "baseline")
    baseline_sha256 = hashlib.sha256(baseline.read_bytes()).hexdigest()

    empty_pycache = source_copy / "hooks" / "__pycache__"
    empty_pycache.mkdir(parents=True)
    (empty_pycache / "stray.pyc").write_bytes(b"")

    with_stray_dir = bundle.build(tmp_path / "with-stray-dir")
    with_stray_dir_sha256 = hashlib.sha256(with_stray_dir.read_bytes()).hexdigest()

    assert with_stray_dir_sha256 == baseline_sha256
    namelist = zipfile.ZipFile(with_stray_dir).namelist()
    assert not any("hooks" in name for name in namelist)
