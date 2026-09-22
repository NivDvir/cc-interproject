"""Run the six staging steps from `staging/e2e.py` once, into a pytest temporary directory, and
assert on each one separately so a failure names the step that broke. Offline: the only `claude`
on PATH is `fixtures/claude_fake`.
"""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

import pytest

from six_laws_kit.write import blocks
from six_laws_kit.write.plan import MARKER_VERSION, POINTER_MARKER

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"staging_{name}", REPO_ROOT / "staging" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


e2e = _load("e2e")
build_home = _load("build_home")

STEP_NAMES = (
    "1 build staging HOME",
    "2 dry run discovers 12",
    "3 install writes the plan",
    "4 --status lists every row",
    "5 re-install is idempotent",
    "6 --uninstall restores all",
)


@pytest.fixture(scope="module")
def staging_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """Build a staging HOME and run all six steps once; return `{step name: (ok, reason)}`."""
    home = tmp_path_factory.mktemp("staging") / "home"
    temp_dirs: list = []
    installer, _note = e2e.installer_path(temp_dirs)
    try:
        results = e2e.run_all(home, installer)
    finally:
        for temp in temp_dirs:
            shutil.rmtree(temp, ignore_errors=True)
    return {name: (ok, reason) for name, ok, reason in results}


@pytest.mark.parametrize("step", STEP_NAMES)
def test_step_passes(staging_run: dict, step: str) -> None:
    ok, reason = staging_run[step]
    assert ok, f"{step}: {reason}"


def test_pointer_markers_match_the_installer(staging_run: dict) -> None:
    """The markers `build_home.py` hard-codes into `code/legacy` are the ones the kit renders."""
    assert blocks.BEGIN.format(id=POINTER_MARKER, v=MARKER_VERSION) == build_home.POINTER_BEGIN
    assert blocks.END.format(id=POINTER_MARKER) == build_home.POINTER_END


def test_builder_refuses_a_non_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "something").write_text("already here\n", encoding="utf-8")
    assert build_home.main(["--out", str(tmp_path)]) == 2
