# discover/ — architecture

Full design: `../../../docs/DESIGN.md` (§2 data flow, §7 Windows/Linux, §8 fixtures).
Signatures: `../../../docs/INTERFACES.md`. This file is a map, not a duplicate of either.

## Files

| File | Job |
|---|---|
| `walk.py` | `os.scandir` walk from a root directory. Finds every `CLAUDE.md`, applies the per-OS skip list (`paths.skip_names()`) at every level it enters, caps the **search for heads** at `max_depth` from the root while walking a tree it has found to any depth, caps total directories scanned, reports progress every 200 directories, and never follows a symlink or reparse point. |
| `forest.py` | Turns the flat list of `CLAUDE.md` paths into nested `Tree`s — a `CLAUDE.md` inside another project's directory becomes a subtree of the nearest project above it, never a root of its own — and applies a selection set with inheritance down to subtrees. |
| `sessions.py` | For each tree, looks up `<claude_dir>/projects/<encoded tree.path>` (trying both `paths.encode_project_dir` candidates) and sets `has_session` / `last_session` from the newest `*.jsonl` file's mtime. |

## Data flow

`walk.find_projects` → `forest.build` → `forest.apply_selection` → `sessions.annotate`, per
`DESIGN.md` §2 ("Scan" step). `cli.py`/`wizard/api.py` are the only callers; nothing in this
package calls into `wizard/`, `heads/`, `write/`, or `manifest/`.

## Import rule

Only the stdlib and the package-root files `run_state` and `paths` (see `STYLE.md`). No
imports between `discover/` and any other category.
