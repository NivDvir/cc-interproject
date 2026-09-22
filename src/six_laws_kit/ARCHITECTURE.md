# six_laws_kit/ — package architecture

Full design: `../../docs/DESIGN.md`. Signatures: `../../docs/INTERFACES.md`. Style: `../../docs/STYLE.md`.
This file is a map, not a duplicate of any of them.

## Category map

| Category | Job |
|---|---|
| package root (`cli.py`, `__main__.py`, `run_state.py`, `paths.py`, `__init__.py`) | Entry point, the shared `Run`/`Tree`/`Row`/`Action` state, and filesystem locations. |
| `discover/` | Walk `$HOME` (or `--root`) for Claude Code projects, build the nested forest, annotate it with session history. |
| `heads/` | Ask each chosen project's own `CLAUDE.md` for its registry row, headless, with a fallback path. |
| `wizard/` | The loopback HTTP server and browser UI (`server.py`, `api.py`, `launch.py`, `assets/`) that drive the install flow; `terminal.py` mirrors it on stdin/stdout when no browser can be opened. |
| `write/` | Turn a `Run`'s plan into exact file text: marked blocks, the registry table, `settings.json` hook merges, the diff-carrying `Action` list, and the one place that writes to disk. |
| `manifest/` | Record what was written (`record.py`), report it (`status.py`), and undo it (`uninstall.py`). |
| `hooks/` | Three standalone programs copied to `~/.claude/hooks/six-laws/`; each runs alone, no shared imports, not even with each other. |
| `texts/` | The static public-text files the installer writes into a reader's `~/.claude/` and projects, plus the loader that reads them. |

## Import rule

A category imports only the stdlib and the package-root modules `run_state` and `paths`, plus its
own sibling modules. Named exceptions (`docs/DESIGN.md` section 2, `docs/STYLE.md`):

- `write/plan.py` may import `texts.loader` — the one place that turns a shipped text file into an
  `Action` payload.
- `write/apply.py` may import `manifest.record` — writing a file and recording it in the manifest
  happen in the same pass.
- `manifest/uninstall.py` may import `write.blocks` and `write.settings` — undoing a marker block or
  a hook merge needs the exact logic that created it.
- `cli.py` and `wizard/api.py` are the only two modules allowed to call across every category; they
  are the orchestrators. `wizard/terminal.py` is not among them: it renders the plan step's diffs
  itself from the plain dict `wizard.api.plan()` returns, the same way `wizard/assets/wizard.js`
  renders them for the browser, instead of importing `write.plan`.
- The three `hooks/*.py` programs import nothing of this package at all — see `hooks/ARCHITECTURE.md`.

`tests/test_architecture.py` enforces this rule by parsing every module's imports; do not weaken it
to make a shortcut compile.

## Where the thing that does X lives

| If you're looking for... | It's in... |
|---|---|
| Argument parsing, exit codes, preflight, dispatch | `cli.py` |
| `python3 -m six_laws_kit` | `__main__.py` |
| The shared `Run` / `Tree` / `Row` / `Action` dataclasses | `run_state.py` |
| `~/.claude` locations, per-OS skip lists, session-dir encoding | `paths.py` |
| Finding every Claude Code project on disk | `discover/walk.py`, `discover/forest.py` |
| Reading `~/.claude/projects/` session history | `discover/sessions.py` |
| The `claude` CLI lookup, capability probe, login check | `heads/preflight.py` |
| The `claude -p` packet and its parsing | `heads/packet.py`, `heads/ask.py` |
| The fallback row when a head doesn't answer | `heads/fallback.py` |
| The wizard's HTTP endpoints | `wizard/api.py`, `wizard/server.py`, `docs/INTERFACES.md` |
| Opening a browser, or deciding one cannot be opened | `wizard/launch.py` |
| The wizard's HTML/CSS/JS | `wizard/assets/` |
| The no-browser terminal flow | `wizard/terminal.py` |
| Building the diff shown at Review | `write/plan.py` |
| Actually writing files | `write/apply.py` |
| Marked-block insertion and stripping | `write/blocks.py` |
| `~/.claude/PROJECT_REGISTRY.md` assembly | `write/registry.py` |
| `~/.claude/settings.json` hook merging | `write/settings.py` |
| The manifest schema, writer, and reader | `manifest/record.py` |
| `--uninstall` | `manifest/uninstall.py` |
| `--status` | `manifest/status.py` |
| The three installed hooks (packet reminder, labor tally, load cap) | `hooks/` |
| Static text bodies (`SIX_LAWS.md`, protocol, pointers, etc.) | `texts/` |
