from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from six_laws_kit import paths
from six_laws_kit.manifest import record, uninstall
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


def _hash_tree(root: Path) -> dict:
    """Hash every file under `root` except the kit's own backup archive, which DESIGN.md §5
    says stays on disk after a default uninstall.
    """
    backups_root = root / "dot-claude" / paths.BACKUPS_SUBDIR
    hashes = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if backups_root in path.parents or path == backups_root:
            continue
        hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _refuse_ask(message: str) -> bool:
    raise AssertionError(f"unexpected prompt during a clean uninstall: {message}")  # noqa: TRY003


def test_apply_then_uninstall_leaves_the_tree_byte_identical(forest_home: Path):
    before = _hash_tree(forest_home)

    run = _make_run(forest_home)
    plan.build(run)
    apply.execute(run, lambda *_args: None)
    assert _hash_tree(forest_home) != before, "install should have changed something"

    exit_code = uninstall.run(run, ask=_refuse_ask)

    assert exit_code == 0
    assert not paths.manifest_path(run.claude_dir).exists()
    assert _hash_tree(forest_home) == before


def _make_fresh_run(home: Path) -> Run:
    """A run whose `claude_dir` does not exist yet, two levels below `home`, so the install has to
    create both levels and record them.
    """
    return Run(
        mode="install",
        home=home,
        claude_dir=home / "nested" / "dot-claude",
        root=home,
        no_browser=True,
    )


def test_install_records_every_directory_it_created(forest_home: Path):
    run = _make_fresh_run(forest_home)
    alpha = forest_home / "alpha"
    run.trees = [Tree(path=alpha, name="Alpha", claude_md=alpha / "CLAUDE.md", selected=True)]
    plan.build(run)
    apply.execute(run, lambda *_args: None)

    manifest = record.load(paths.manifest_path(run.claude_dir))
    created_dirs = {Path(entry["path"]) for entry in manifest["entries"] if entry["kind"] == "created_dir"}
    assert run.claude_dir in created_dirs
    assert run.claude_dir.parent in created_dirs
    assert forest_home not in created_dirs, "a directory that already existed must not be tracked"


def test_uninstall_removes_a_created_directory_once_it_is_empty(forest_home: Path):
    """A `created_dir` entry is undone after the files inside it, deepest first, and only while
    the directory is empty.
    """
    run = _make_run(forest_home)
    made = forest_home / "made" / "deep"
    made.mkdir(parents=True)
    target = made / "SIX_LAWS.md"
    target.write_text(_TEXTS["SIX_LAWS.md"], encoding="utf-8")
    record.write(
        {
            "schema": 1,
            "entries": [
                {"kind": "created_dir", "path": str(made.parent)},
                {"kind": "created_dir", "path": str(made)},
                {"kind": "created_file", "path": str(target), "sha256_after": record.sha256(target)},
            ],
        },
        paths.manifest_path(run.claude_dir),
    )

    assert uninstall.run(run, ask=_refuse_ask) == 0

    assert not made.exists()
    assert not made.parent.exists(), "the now-empty parent should be removed too"
    assert forest_home.exists(), "a directory the install did not create must survive uninstall"


def test_uninstall_with_no_manifest_reports_and_returns_zero(forest_home: Path):
    run = _make_run(forest_home)
    assert uninstall.run(run, ask=_refuse_ask) == 0


def test_uninstall_asks_before_touching_a_file_modified_since_install(forest_home: Path):
    run = _make_run(forest_home)
    plan.build(run)
    apply.execute(run, lambda *_args: None)

    six_laws_path = run.claude_dir / "SIX_LAWS.md"
    six_laws_path.write_text(_TEXTS["SIX_LAWS.md"] + "an edit nobody recorded\n", encoding="utf-8")
    modified_content = six_laws_path.read_text(encoding="utf-8")

    prompts: list[str] = []

    def _decline(message: str) -> bool:
        prompts.append(message)
        return False

    uninstall.run(run, ask=_decline)

    assert prompts, "uninstall should have asked about the modified file"
    assert six_laws_path.exists()
    assert six_laws_path.read_text(encoding="utf-8") == modified_content

    project_registry = run.claude_dir / "PROJECT_REGISTRY.md"
    assert not project_registry.exists()


def test_restore_backups_flag_restores_files_the_default_pass_could_not(forest_home: Path):
    dot_claude_md = forest_home / "dot-claude" / "CLAUDE.md"
    original_pre_install = dot_claude_md.read_text(encoding="utf-8")

    run = _make_run(forest_home)
    plan.build(run)
    apply.execute(run, lambda *_args: None)
    assert dot_claude_md.read_text(encoding="utf-8") != original_pre_install

    dot_claude_md.write_text(dot_claude_md.read_text(encoding="utf-8") + "user edit\n", encoding="utf-8")

    uninstall.run(run, restore_backups=True, ask=lambda _message: True)

    assert dot_claude_md.read_text(encoding="utf-8") == original_pre_install


def test_record_new_backup_dir_matches_where_apply_wrote_backups(forest_home: Path):
    run = _make_run(forest_home)
    plan.build(run)
    apply.execute(run, lambda *_args: None)
    manifest = record.load(paths.manifest_path(run.claude_dir))
    assert Path(manifest["backup_dir"]).exists()
