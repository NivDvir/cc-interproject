# write/

Turns a `Run` into the exact text that should land on disk, and then writes it. Nothing here talks
to the network or spawns a process; every function is pure text-in, text-out except `apply.execute`,
which is the one place that touches the filesystem for this category.

- `blocks.py` — the `<!-- six-laws-kit:begin/end -->` marker convention: render a block, detect one,
  insert one at the end of a file (tracking whether a blank line or trailing newline had to be
  added), strip one back out. `replace_block(text, marker_id, version, body)` (added past v1 of
  `INTERFACES.md`, not in the original signature list) swaps an existing block's body and version
  in place — position and surrounding text untouched — for a re-install whose content changed;
  `plan.py` uses it for `PROJECT_REGISTRY.md` so a second install refreshes the table instead of
  appending a duplicate.
- `registry.py` — renders `PROJECT_REGISTRY.md`'s table from the rows the Heads step collected.
- `settings.py` — loads, previews, and idempotently merges the kit's three hook entries into a
  `~/.claude/settings.json`-shaped dict, and removes them again on uninstall.
- `plan.py` — `build(run)` walks every module the run wants installed and produces the ordered list
  of `Action`s (each carrying its own in-memory unified diff); `render_text` prints them.
- `apply.py` — `execute(run, on_progress)` performs the plan: creates directories (tracked so
  uninstall can remove exactly the ones it made), backs up any pre-existing target, writes
  atomically, and records everything into the manifest that `manifest/record.py` defines. On a
  re-install it loads the previous manifest first (`record.new(run, stamp, previous=...)`) so
  entries for targets an idempotent step skipped this run are not forgotten, then deduplicates by
  path (last write wins) before writing.

Import rule (STYLE.md): only the stdlib, `run_state`, `paths`, sibling modules in this package, and
`texts.loader` — the one named exception, since `plan.build` is the sole place that turns the kit's
shipped text files into `Action` payloads and the fixed `plan.build(run)` signature has nowhere else
to receive that text from.
