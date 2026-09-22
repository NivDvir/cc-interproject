# manifest/

Everything that reads or writes `~/.claude/interproject.manifest.json`, schema 1 (DESIGN.md §5).

- `record.py` — build a fresh manifest header for a run (`new`), append an entry to it, write it
  atomically, load one back, and hash a file for it.
- `uninstall.py` — walks a loaded manifest's `entries[]` in reverse and undoes each one by kind:
  `created_file` deletes when unmodified else asks; `inserted_block` strips the marker (via
  `write.blocks.strip`) and undoes the recorded blank-line/trailing-newline addition; `backup` (used only for the plain `append_line` entry, which has no marker to
  find) restores the file's pre-install bytes when unmodified, else asks. `--restore-backups` adds a
  second, blunter pass that copies every file under the manifest's `backup_dir` back over its
  original location, regardless of what the per-kind pass already did.
- `status.py` — reports what a manifest says is installed, cross-checked against what is still on
  disk (each entry's current sha256 against what was recorded), and each tree's head pulse
  (`self` vs `installer`) from `heads[]`.

Import rule: stdlib, `run_state`, `paths`, this category's own siblings, and `write.blocks` — the
same named cross-category exception as `write/plan.py`, since undoing a block requires the exact
same logic that created it.
