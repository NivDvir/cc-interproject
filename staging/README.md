# staging/

A throwaway HOME that looks like a real Claude Code user's machine, and an end-to-end run of the
installer against it. Not shipped: nothing under `src/` imports anything here.

- `build_home.py --out DIR` plants twelve projects, five decoys, a used `.claude/`, and junk.
- `templates/` holds every file's content; the builder only places it.
- `e2e.py --home DIR [--keep]` runs six steps (build, dry run, install, status, re-install,
  uninstall), printing PASS/FAIL each; `tests/staging` calls the same functions.
- Only `fixtures/claude_fake/claude` is ever called. See `../docs/STAGING.md`.
