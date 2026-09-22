# Architecture

Full design: `docs/DESIGN.md`. Behaviour: `publication/cc-interproject/SPEC.md` (parent repo).
This file is a map, not a duplicate of either.

## Category map

| Category | Job |
|---|---|
| `src/cc_interproject/` root (`cli.py`, `run_state.py`, `paths.py`) | Entry point, shared state, filesystem locations. |
| `discover/` | Walk `$HOME`, find projects (a directory with its own `CLAUDE.md`), build the forest, annotate with session history. |
| `heads/` | Ask each chosen project's own `CLAUDE.md` for its registry row, headless, with a fallback path. |
| `wizard/` | The local HTTP server and browser UI that drives the install flow; `terminal.py` mirrors it without a browser. |
| `write/` | Turn a plan into file writes: the registry and the marked blocks. |
| `manifest/` | Record what was written, and undo it on `--uninstall`. |
| `texts/` | The static public-text files the installer writes, plus the loader that reads them. |
| `tools/` | Build- and repo-maintenance scripts, run by a human or CI, never by the installer. |

## Import rule

A category imports only the stdlib, `run_state`, `paths`, and its own siblings. `cli.py` and
`wizard/api.py` are the only places allowed to call across categories — they are the
orchestrators.

`tests/test_architecture.py` enforces this rule by inspecting imports; do not weaken it to make
a shortcut compile.

## Where the thing that does X lives

| If you're looking for... | It's in... |
|---|---|
| Finding every Claude Code project on disk | `discover/walk.py`, `discover/forest.py` |
| Reading `~/.claude/projects/` session history | `discover/sessions.py` |
| The `claude -p` packet and its parsing | `heads/packet.py`, `heads/ask.py` |
| The fallback row when a head doesn't answer | `heads/fallback.py` |
| The wizard's HTTP endpoints | `wizard/api.py`, `docs/INTERFACES.md` |
| The wizard's HTML/CSS/JS | `wizard/assets/` |
| The no-browser terminal flow | `wizard/terminal.py` |
| Building the diff shown at Review | `write/plan.py` |
| Actually writing files | `write/apply.py` |
| Marked-block insertion and stripping | `write/blocks.py` |
| `~/.claude/PROJECT_REGISTRY.md` assembly | `write/registry.py` |
| The manifest schema and writer | `manifest/record.py` |
| `--uninstall` | `manifest/uninstall.py` |
| `--status` | `manifest/status.py` |
| Static text bodies (INTERPROJECT_LAWS.md, protocol, etc.) | `texts/` |
| The zipapp build | `tools/bundle.py`, `tools/ARCHITECTURE.md` |
