# heads/

Asks each chosen project's own `CLAUDE.md` for its registry row, per Law 1: the project describes
itself, the installer never writes an opinion in its place unless the project cannot answer.

## Files

- `preflight.py` — locates the `claude` CLI (`find_claude`), probes which optional flags it
  supports (`probe_capabilities`), and confirms it is logged in (`auth_ping`). Runs once, before
  any head is asked.
- `packet.py` — the exact prompt sent to every head (`PACKET`), the JSON Schema its answer must
  satisfy (`ROW_SCHEMA`), and the command line that sends it (`build_command`).
- `ask.py` — `start()` launches a background `ThreadPoolExecutor` (default 4 workers) over the
  selected trees; each tree gets `ask_one()`, whose result is parsed by `parse_row()` through three
  tiers (`structured_output` → fenced/plain JSON in `result` → first balanced `{...}` in `result`)
  before falling back. `is_auth_failure_text()` recognises a local login problem so it is never
  counted as a failure of the project being asked.
- `fallback.py` — when a head cannot answer (or has none), `row_from_claude_md()` builds the row
  directly from the project's own `CLAUDE.md`: the first `# ` heading (else the directory name) for
  `name`, the first paragraph after it, cut to 40 words, for `owns`, `NOT STATED` for the rest.
  Every row this module produces has `written_by="installer"`; it never claims `"self"`.

## Contract

A row is `written_by="self"` iff the head's own answer supplied a non-empty `name` and `owns`;
anything else — a timeout, a non-zero exit, unparsable output, or a missing/empty required field —
is `written_by="installer"` via `fallback.row_from_claude_md`, with `status` set to how it failed
(`"timeout"`, `"error"`, `"authfail"`, or `"fallback"` for output that parsed as JSON but not into a
usable row). Only `"ok"` is `written_by="self"`. See `docs/DESIGN.md` section 4 and
`docs/INTERFACES.md` for the exact signatures and the head-call command line.

## Import rule

Only the stdlib, `six_laws_kit.run_state`, `six_laws_kit.paths`, and this package's own siblings.
`preflight.py` imports `ask.is_auth_failure_text` (a sibling); nothing here imports `discover/`,
`write/`, `wizard/`, or `manifest/`.
