# six-laws-kit — design (v1, 2026-09-22)

Behaviour is specified in `../../../publication/six-laws-kit/SPEC.md`. This file fixes the shape of
the code. `INTERFACES.md` fixes the signatures. `STYLE.md` fixes the style.

## 1. Repo tree (every source file ≤ 400 lines)

```
six-laws-kit/
  README.md LICENSE CHANGELOG.md SECURITY.md PRIVACY.md CODEOWNERS ARCHITECTURE.md CLAUDE.md
  ruff.toml pyproject.toml .pre-commit-config.yaml
  .github/workflows/ci.yml .github/workflows/release.yml .github/ISSUE_TEMPLATE/bug_report.md
  docs/DESIGN.md docs/INTERFACES.md docs/STYLE.md
  tools/ARCHITECTURE.md tools/bundle.py        zipapp -> dist/install.py + SHA256SUMS; --check for CI
  src/six_laws_kit/
    ARCHITECTURE.md __init__.py (VERSION) __main__.py
    cli.py          argparse, modes (install | --dry-run | --uninstall | --status), preflight, exit codes
    run_state.py    Run / Tree / Row / Action dataclasses — the only shared state
    paths.py        Path.home() locations, per-OS skip lists, ~/.claude/projects encoding
    discover/  ARCHITECTURE.md walk.py forest.py sessions.py
    heads/     ARCHITECTURE.md preflight.py packet.py ask.py fallback.py
    wizard/    ARCHITECTURE.md server.py api.py launch.py terminal.py
               assets/ARCHITECTURE.md assets/index.html assets/wizard.css assets/wizard.js assets/icons.svg
    write/     ARCHITECTURE.md plan.py apply.py blocks.py registry.py settings.py
    manifest/  ARCHITECTURE.md record.py uninstall.py status.py
    hooks/     ARCHITECTURE.md packet_reminder.py labor_tally.py load_cap.py   (standalone programs)
    texts/     ARCHITECTURE.md loader.py SIX_LAWS.md INTERPROJECT_PROTOCOL.md PRIOR_ART.md
               DISPATCHER_QUEUE.md REGISTRY_HEADER.md PROJECT_POINTER.md ACCOUNT_POINTER.md
               PACKET_REMINDER.md
  tests/       mirrors src 1:1; conftest.py; test_architecture.py (import gate)
  fixtures/    README.md forest/ transcripts/ claude_fake/claude claude_fake/claude.cmd
```

Import rule: a category imports only the stdlib, `run_state`, `paths`, and its own siblings. `cli.py`
and `wizard/api.py` are the only places that call across categories. The three hook programs share
no module at all: each is copied as one file to `~/.claude/hooks/six-laws/` and registered as
`python3 <file>` (or `py -3 <file>`), so they must run alone.

## 2. Data flow

```
cli.main()
  run_state.new_run(args)
  heads.preflight.find_claude(run)         exit 3 if absent
  heads.preflight.probe_capabilities(run)  is --json-schema supported?
  heads.preflight.auth_ping(run)           exit 4 if not logged in
  --uninstall -> manifest.uninstall.run(run) ; --status -> manifest.status.run(run)
  else wizard.launch.open_ui(run) or, with --no-browser / no display, wizard.terminal.run(run)

Welcome   api.state
Scan      api.scan_start -> discover.walk.find_projects -> discover.forest.build -> discover.sessions.annotate
          api.set_selection -> discover.forest.apply_selection
Modules   api.set_modules (routing pre-unticked when write.settings.same_purpose_hooks(run) is non-empty)
Heads     api.heads_start -> heads.ask.start (ThreadPoolExecutor, 4 workers)
             per tree: heads.packet.build_command -> heads.ask.ask_one -> heads.ask.parse_row
                       or heads.fallback.row_from_claude_md
Review    api.plan -> write.plan.build (uses write.registry.render, write.blocks.render,
                       write.settings.preview, texts.loader.read); unified diffs in memory
Install   api.install_start -> write.apply.execute -> manifest.record.write
Done      api.done (paste block, counts, uninstall command) ; api.quit -> server shutdown
```
`--dry-run` ends after Review: the plan is rendered, nothing is written, exit 0.

## 3. Wizard <-> Python

Server: `http.server.ThreadingHTTPServer` on `127.0.0.1`, port 0. A per-run token
(`secrets.token_hex(16)`) is in the opened URL (`/?t=`), embedded in the page as one JS const, and
required as header `X-Kit-Token` on every `/api/*` call. Requests with a non-loopback `Host` or a
foreign `Origin` are refused with 403. There are no asset sub-requests: `server.render_page()` reads
`assets/index.html` and substitutes `<!--@css-->`, `<!--@js-->`, `<!--@icons-->` with the sibling files
at request time — one HTML response, works offline. Progress is plain polling (scan 400 ms, heads
700 ms, install 300 ms) of a lock-guarded dict. Shutdown: `POST /api/quit` answers 200, then
`threading.Timer(0.3, httpd.shutdown)`; the page also sends `navigator.sendBeacon('/api/quit')` on
`pagehide`; a watchdog shuts the server after 15 minutes idle; Ctrl-C always wins. The endpoint
table is in `INTERFACES.md`.

## 4. The head call

```
claude -p --model sonnet --allowedTools Read Glob --disallowedTools Write Edit Bash WebFetch
       --output-format json [--json-schema <ROW_SCHEMA>] --max-turns 6 --max-budget-usd 0.25
```
cwd = the project directory, `input=PACKET`, `timeout=120`, at most 4 in parallel. `--json-schema` is
capability-probed from `claude --help` once (v2.1.268 has it). Parse tiers: envelope
`structured_output` → `result` as JSON (fence stripped) → first balanced `{…}` in `result` → fallback.
A row is `written-by: self` iff `name` and `owns` are non-empty; other fields default to `NOT STATED`.
Auth-failure text is recognised and reported as a local problem, never counted against a head.
Fallback (`heads/fallback.py`): name = first `# ` heading else directory name; owns = first
non-heading paragraph cut to 40 words; the rest `NOT STATED`; `written-by: installer`.

## 5. Manifest (`~/.claude/six-laws.manifest.json`, schema 1)

Header: kit name/version/url, installed_at (UTC ISO), modules, python, platform, hook_interpreter,
backup_dir. `entries[]` kinds: `created_file` (path, sha256_after, bytes), `backup` (path, backup_path,
sha256_before), `inserted_block` (path, marker_id, marker_version, begin, end, sha256_before,
sha256_after, bytes_added, leading_blank_added, trailing_newline_added), `settings_hooks` (path,
sha256_before, sha256_after, added[] of {event, matcher, command, timeout}). `heads[]`: path,
written_by, status, seconds. Markers: `<!-- six-laws-kit:begin id=<id> v=<n> -->` /
`<!-- six-laws-kit:end id=<id> -->`.

Uninstall walks entries in reverse. `created_file`: sha matches → delete, else ask. `inserted_block`:
sha matches → strip inclusive and undo the recorded blank/newline; sha differs but both markers
present exactly once → strip and report; markers gone → leave and report. `settings_hooks`: remove
hook dicts matched by their `command` string (never by index), drop groups/events that become empty,
never restore a whole settings.json. Backups stay on disk; `--uninstall --restore-backups` restores.

## 6. Hooks (`~/.claude/hooks/six-laws/`, state in `~/.claude/six-laws-state/`)

| file | event | stdin | stdout | state files |
|---|---|---|---|---|
| packet_reminder.py | UserPromptSubmit | {session_id, cwd, prompt} | additionalContext = last tally + `texts/PACKET_REMINDER.md` | reads+deletes `head-tally.<sid>`; writes `turn-loads.<sid>` = `"0 6"`; deletes `turn-delegated.<sid>` |
| labor_tally.py | Stop | {session_id, transcript_path} | nothing | writes `head-tally.<sid>` e.g. `Read×7 Bash×3 Delegate×1`; reaps files > 1 day |
| load_cap.py | PreToolUse | {session_id, tool_name, tool_input} | allow = silent exit 0; deny = permissionDecision deny + reason | increments `turn-loads.<sid>` (`"<count> <threshold>"`); `turn-delegated.<sid>` switches the cap off |

Invariants (from the originals, kept verbatim): UserPromptSubmit never fires for sub-agents, so the
existence of `turn-loads.<sid>` is what marks a head — no file → allow silently, workers are never
capped; allow is always silent (emitting "allow" would bypass the user's own deny rules); every deny
raises the stored threshold by 6 so the head can always proceed; every hook exits 0 on every path.
Session id sanitised `re.sub(r"[^A-Za-z0-9._-]", "_", sid)[:128]`. Matchers registered: UserPromptSubmit
and Stop with none; PreToolUse with `Agent|Task|SendMessage|Read|Grep|Glob|Bash|WebFetch`.
Settings merge (`write/settings.py`): skip if any entry anywhere already has the exact command;
else append to the group with an equal matcher, else a new group; preserve key order; atomic
`os.replace` after backup. `same_purpose_hooks(run)` detects existing hooks whose command basename
contains `packet-wrap`, `labor-tally`, `load-cap` (the owner's own bash hooks) or the kit's names.
Each hook derives its state directory from home: an explicit `HOME` env var wins when set, else
`Path.home()`. This matters only on Windows, where `Path.home()` reads `USERPROFILE` and ignores
`HOME` — a caller (this repo's own tests included) that sandboxes the hook by setting only `HOME`
would otherwise land outside the sandbox there. `run_state.new_run` resolves `home` the same way,
via `paths.home_dir()`, so a `--root`-sandboxed install and its hooks agree on where `~/.claude`
(or its `dot-claude` stand-in) is even on Windows; the hooks keep their own copy of the same two
lines since they may import nothing from the package.

## 7. Windows and Linux

Hook interpreter: `shutil.which("py")` → `py -3 "<posix path>"`; else `python3 "<posix path>"`
(prefer `which("python3")` over `sys.executable`, which may be a venv). Recorded in the manifest.
Paths written with `Path.as_posix()` and double-quoted. `claude` found with `shutil.which` (matches
`claude.cmd`); subprocess always a list, never `shell=True`. Skip lists: POSIX `.git node_modules
venv .venv __pycache__ .cache .npm .cargo Library .Trash Pictures Movies Music`; Windows adds `AppData
OneDrive $Recycle.Bin`; symlinks and reparse points skipped; depth cap 6; hard cap 200,000 directories
with a live counter; the Scan step names every root it skipped. Session-dir encoding is lossy
(`/`, `.`, `_` → `-`): always encode forward from the real path and match against the listing, never
decode. `.md` written with `newline="\n"`; block-strip tolerates CRLF. On Linux without
`DISPLAY`/`WAYLAND_DISPLAY`, or under WSL, go straight to the terminal UI; the URL is always printed.

## 8. Tests and CI

`tests/` mirrors `src/`; `fixtures/forest/` is a fake HOME with: `alpha/CLAUDE.md`, `alpha/sub/CLAUDE.md`,
`alpha/node_modules/pkg/CLAUDE.md` (must be skipped), `beta/CLAUDE.md`, `beta/.venv/lib/CLAUDE.md`,
`gamma/README.md` (no CLAUDE.md), `.Trash/old/CLAUDE.md`, `dot-claude/CLAUDE.md`,
`dot-claude/settings.json` (one foreign hook that must survive), `dot-claude/projects/<encoded alpha>/<uuid>.jsonl`.
`fixtures/transcripts/`: `head_turn.jsonl`, `worker_turn.jsonl`, `malformed.jsonl`. `fixtures/claude_fake/claude`
(+ `claude.cmd`): a Python program that emits a real `--output-format json` envelope and switches on
`KIT_FAKE_MODE=ok|slow|garbage|authfail|nonzero|noschema`. `conftest.py` puts it first on PATH and
points HOME at a copy of the forest. CI matrix: ubuntu/macos/windows × Python 3.9 and 3.13: ruff check,
ruff format --check, pytest -q, `tools/bundle.py --check`, `dist/install.py --dry-run --no-browser
--root fixtures/forest`. `--root <dir>` is a documented testing flag.

## 9. Decisions taken (do not re-open)

zipapp bundle named `install.py` (README: download then run). Routing module ON by default,
pre-unticked when same-purpose hooks exist. Head-call model fixed to sonnet, not user-selectable in v0.1.
`PACKET_REMINDER.md` is a neutral public statement of the SELF/DELEGATE rule, approved by Niv.
The kit never edits or removes a hook it did not write.
