# Fixtures

What each fixture proves, and how to drive the fake `claude` binary.

## fixtures/forest/

A fake HOME for `discover/walk.py` and `discover/forest.py`.

- `alpha/CLAUDE.md` — a top-level project root; the ordinary case.
- `alpha/sub/CLAUDE.md` — a nested subtree of `alpha`, must appear under it, not as its own root.
- `alpha/node_modules/pkg/CLAUDE.md` — vendored material; must be skipped by the skip list, never
  discovered as a project.
- `beta/CLAUDE.md` — a second, independent top-level project root.
- `beta/.venv/lib/CLAUDE.md` — vendored material inside a virtualenv; must be skipped.
- `gamma/README.md` — a project folder with documentation but no `CLAUDE.md`; must never be discovered.
- `.Trash/old/CLAUDE.md` — proves directories under `.Trash` are skipped entirely.
- `dot-claude/CLAUDE.md` — stands in for `~/.claude/CLAUDE.md`; a top-level root like any other.
- `dot-claude/projects/<encoded alpha>/<uuid>.jsonl` — a session transcript for `alpha`, used by
  `discover/sessions.py` to set `has_session`/`last_session`. See
  `fixtures/forest/dot-claude/projects/README.md` for why the encoded directory name must be
  recomputed, not reused, once the forest is copied into a temporary HOME.

Every `CLAUDE.md` here (other than the two vendored-material ones, which exist only to prove they are
skipped) has a `# <Name>` heading and one or two prose paragraphs about a made-up project, so the
fallback row extractor (`heads/fallback.py`) has real material to read.

## fixtures/claude_fake/

`claude` (+ the Windows shim `claude.cmd`) stands in for the real `claude -p` head call. It accepts and
ignores every flag from `DESIGN.md` section 4 (`-p`, `--model`, `--allowedTools`/`--disallowedTools`,
`--output-format`, `--json-schema <schema>`, `--max-turns`, `--max-budget-usd`), plus `--help` and
`--version`. It reads (and discards) the packet on stdin, then answers according to `KIT_FAKE_MODE`:

| `KIT_FAKE_MODE` | behavior | exit code |
|---|---|---|
| `ok` (default) | envelope with `structured_output` set, row derived from `./CLAUDE.md` in cwd | 0 |
| `noschema` | same row, but no `structured_output`; `result` is a fenced ` ```json ` block instead | 0 |
| `garbage` | `result` is `"I cannot help with that."`, no `structured_output` | 0 |
| `slow` | sleeps `KIT_FAKE_SLEEP` seconds (default 5), then behaves like `ok` | 0 |
| `authfail` | `{"type":"result","is_error":true,"result":"Not logged in. Please run /login"}` | 1 |
| `nonzero` | prints `boom` to stderr | 2 |

Point `conftest.py` at this file first on `PATH` so `shutil.which("claude")` finds it instead of the
real CLI.
