# staging/

A throwaway HOME that looks like a real Claude Code user's machine, and an end-to-end run of the
installer against it. Not shipped: nothing under `src/` imports anything here.

- `build_home.py --out DIR` plants sixteen projects (one of them a tree four levels deep), six
  decoys, a used `.claude/`, and junk.
- `templates/` holds every file's content; the builder only places it.
- `e2e.py --home DIR [--keep]` runs seven steps (build, dry run, install, status, re-install,
  uninstall, tree shape), printing PASS/FAIL each; `tests/staging` calls the same functions.
- `tree_shape.py` is step 7: it reads the forest back through the kit's own Scan step and checks
  that one tree nests to any depth in both the API's JSON and the terminal rendering.
- Only `fixtures/claude_fake/claude` is ever called. See `../docs/STAGING.md`.
