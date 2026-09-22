from __future__ import annotations

from pathlib import Path

import pytest

from six_laws_kit import paths
from six_laws_kit.manifest import record
from six_laws_kit.run_state import Run, Tree
from six_laws_kit.write import apply, plan

_TEXTS = {
    "SIX_LAWS.md": "law text\n",
    "INTERPROJECT_PROTOCOL.md": "protocol text\n",
    "PRIOR_ART.md": "prior art text\n",
    "DISPATCHER_QUEUE.md": "queue text\n",
    "REGISTRY_HEADER.md": "# Project registry\n\nRead before any cross-project work.\n",
    "ACCOUNT_POINTER.md": "Read the six laws before any cross-project work.\n\n---\n\nmore prose here.\n",
    "PROJECT_POINTER.md": "Reach other projects only through their heads.\n",
}


@pytest.fixture(autouse=True)
def _fake_texts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("six_laws_kit.texts.loader.read", lambda name: _TEXTS[name])


def _make_run(home: Path) -> Run:
    run = Run(mode="install", home=home, claude_dir=home / "dot-claude", root=home, no_browser=True)
    alpha = Tree(path=home / "alpha", name="Alpha", claude_md=home / "alpha" / "CLAUDE.md", selected=True)
    beta = Tree(path=home / "beta", name="Beta", claude_md=home / "beta" / "CLAUDE.md", selected=True)
    run.trees = [alpha, beta]
    return run


def test_execute_writes_files_and_a_matching_manifest(forest_home: Path):
    run = _make_run(forest_home)
    plan.build(run)
    progress_calls = []
    manifest_path = apply.execute(
        run, lambda target, completed, total: progress_calls.append((target, completed, total))
    )

    assert manifest_path == paths.manifest_path(run.claude_dir)
    assert manifest_path.exists()
    manifest = record.load(manifest_path)
    assert manifest["schema"] == 1

    assert len(progress_calls) == len(run.plan)
    assert progress_calls[-1][1:] == (len(run.plan), len(run.plan))

    assert (run.claude_dir / "SIX_LAWS.md").read_text(encoding="utf-8") == _TEXTS["SIX_LAWS.md"]
    assert (run.claude_dir / "PROJECT_REGISTRY.md").exists()

    kinds = [entry["kind"] for entry in manifest["entries"]]
    assert kinds.count("created_file") >= 5
    assert "inserted_block" in kinds
    assert "backup" in kinds


def test_execute_writes_the_manifest_so_far_and_reraises_on_os_error(
    forest_home: Path, monkeypatch: pytest.MonkeyPatch
):
    run = _make_run(forest_home)
    plan.build(run)
    original_write_atomic = apply._write_atomic
    calls = {"n": 0}

    def _flaky_write(target: Path, text: str, manifest: dict) -> None:
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk full")  # noqa: TRY003
        original_write_atomic(target, text, manifest)

    monkeypatch.setattr(apply, "_write_atomic", _flaky_write)
    with pytest.raises(OSError):
        apply.execute(run, lambda *_args: None)

    manifest_path = paths.manifest_path(run.claude_dir)
    assert manifest_path.exists()
    manifest = record.load(manifest_path)
    assert len(manifest["entries"]) == 1
