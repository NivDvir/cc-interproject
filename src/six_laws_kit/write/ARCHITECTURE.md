# write/

Turns a `Run` into the exact text that should land on disk, and then writes it. Nothing here talks
to the network or spawns a process; every function is pure text-in, text-out except `apply.execute`,
which is the one place that touches the filesystem for this category.

- `blocks.py` — the `<!-- six-laws-kit:begin/end -->` marker convention: render a block, detect one,
  insert one at the end of a file (tracking whether a blank line or trailing newline had to be
  added), strip one back out.
- `registry.py` — renders `PROJECT_REGISTRY.md`'s table from the rows the Heads step collected.
- `settings.py` — loads, previews, and idempotently merges the kit's three hook entries into a
  `~/.claude/settings.json`-shaped dict, and removes them again on uninstall.
- `plan.py` — `build(run)` walks every module the run wants installed and produces the ordered list
  of `Action`s (each carrying its own in-memory unified diff); `render_text` prints them.
- `apply.py` — `execute(run, on_progress)` performs the plan: creates directories, backs up any
  pre-existing target, writes atomically, and records everything into the manifest that
  `manifest/record.py` defines.

Import rule (STYLE.md): only the stdlib, `run_state`, `paths`, sibling modules in this package, and
`texts.loader` — the one named exception, since `plan.build` is the sole place that turns the kit's
shipped text files into `Action` payloads and the fixed `plan.build(run)` signature has nowhere else
to receive that text from.
