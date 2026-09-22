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

## Windows: the `.cmd` shim

A real, npm-installed `claude` resolves on Windows to `claude.cmd`, a batch file. `CreateProcess`
cannot start a batch file directly (no PE header) — it must go through `cmd.exe`. `paths.is_windows_shim`
detects this (via `shutil.which`, which already does the PATHEXT-aware resolution) and
`paths.windows_shim_argv` rewrites the argv to `[COMSPEC or cmd.exe, "/d", "/c", <resolved path>, *rest]`;
`ask_one`, `probe_capabilities`, and `auth_ping` all route their `subprocess.run` argv through it.

Two options were considered for finding the real interpreter behind the shim:

- **Parse the `.cmd` to find the underlying `node`/script call it makes**, then invoke that directly.
  Rejected: npm's shim format is undocumented and has changed across npm versions, the target
  script's own argv handling would still need reproducing, and the kit's own `claude_fake` fixture
  does not even use node — a parser tuned to one shim shape would not generalise.
- **Run the shim itself through `cmd.exe /d /c`** (chosen). `cmd.exe` is a real executable, so
  `CreateProcess` starts it fine, and it knows how to run a batch file. `/d` skips
  `AutoRun` registry commands (no surprise output mixed into the head's JSON envelope); `/c` runs
  the given command and exits. This works for any shim, whatever it launches underneath.

The one caveat: `cmd.exe /c` re-parses its command line with its own quoting rules, which mishandle
an argument that itself contains multiple quoted segments — exactly the shape of `--json-schema`'s
JSON value once it also needs its own quotes. Rather than rely on `subprocess.list2cmdline`'s
argv-quoting surviving a second, different quoting pass, `ask_one` drops `--json-schema` whenever it
is about to route through the shim and leans on `parse_row`'s fenced/balanced-brace fallback tiers
instead. `probe_capabilities` still reports whether the CLI supports the flag (for the manifest);
only sending it is skipped.

A second consequence of the `cmd.exe` hop: `cmd.exe` spawns the real interpreter as its own child,
so on a timeout, killing only the top-level process (what `subprocess.run`'s own timeout handling
does) leaves that child running and holding the inherited stdout/stderr pipes open — the
`communicate()` call draining them afterward would then block until the orphan exits on its own,
defeating the timeout. `ask_one` manages the subprocess itself (`Popen` + `communicate(timeout=)`)
so that on `TimeoutExpired` it can call `taskkill /F /T /PID <pid>` instead of `Popen.kill()`,
killing the whole tree. Off Windows this is a plain `Popen.kill()`, identical to before.

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
