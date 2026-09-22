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
               assets/ARCHITECTURE.md assets/index.html assets/wizard.css
               assets/wizard.js (controller) assets/wizard2.js (DOM builders) assets/icons.svg
    write/     ARCHITECTURE.md plan.py apply.py blocks.py registry.py
    manifest/  ARCHITECTURE.md record.py uninstall.py status.py
    texts/     ARCHITECTURE.md loader.py SIX_LAWS.md INTERPROJECT_PROTOCOL.md PRIOR_ART.md
               DISPATCHER_QUEUE.md REGISTRY_HEADER.md PROJECT_POINTER.md ACCOUNT_POINTER.md
  tests/       mirrors src 1:1; conftest.py; test_architecture.py (import gate)
  fixtures/    README.md forest/ claude_fake/claude claude_fake/claude.cmd
```

Import rule: a category imports only the stdlib, `run_state`, `paths`, and its own siblings. `cli.py`
and `wizard/api.py` are the only places that call across categories.

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
Heads     api.heads_start -> heads.ask.start (ThreadPoolExecutor, 4 workers)
             per tree: heads.packet.build_command -> heads.ask.ask_one -> heads.ask.parse_row
                       or heads.fallback.row_from_claude_md
Review    api.plan -> write.plan.build (uses write.registry.render, write.blocks.render,
                       texts.loader.read); unified diffs in memory
Install   api.install_start -> write.apply.execute -> manifest.record.write
Done      api.done (paste block, counts, uninstall command) ; api.quit -> server shutdown
```
`--dry-run` ends after Review: the plan is rendered, nothing is written, exit 0.

## 3. Wizard <-> Python

Server: `http.server.ThreadingHTTPServer` on `127.0.0.1`, port 0. A per-run token
(`secrets.token_hex(16)`) is in the opened URL (`/?t=`), embedded in the page as one JS const, and
required as header `X-Kit-Token` on every `/api/*` call. Requests with a non-loopback `Host` or a
foreign `Origin` are refused with 403. There are no asset sub-requests: `server.render_page()` reads
`assets/index.html` and substitutes `<!--@css-->`, `<!--@js-->`, `<!--@js2-->`, `<!--@icons-->` with
the sibling files at request time — one HTML response, works offline. The JS is two files only
because of the 400-line cap: `wizard.js` is the controller, `wizard2.js` the DOM builders, and they
share one global scope in document order. Progress is plain polling (scan 400 ms, heads
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

Header: kit name/version/url, installed_at (UTC ISO), python, platform, backup_dir. `entries[]`
kinds: `created_file` (path, sha256_after, bytes), `created_dir` (path), `backup` (path,
backup_path, sha256_before), `inserted_block` (path, marker_id, marker_version, begin, end,
sha256_before, sha256_after, bytes_added, leading_blank_added, trailing_newline_added). `heads[]`:
path, written_by, status, seconds. Markers: `<!-- six-laws-kit:begin id=<id> v=<n> -->` /
`<!-- six-laws-kit:end id=<id> -->`.

Uninstall walks entries in reverse. `created_file`: sha matches → delete, else ask. `inserted_block`:
sha matches → strip inclusive and undo the recorded blank/newline; sha differs but both markers
present exactly once → strip and report; markers gone → leave and report. `created_dir`: remove
when empty. Backups stay on disk; `--uninstall --restore-backups` restores.

## 6. Routing module — not in this kit

The SELF/DELEGATE routing policy and its three hooks are not part of v0.1 (see section 9). Their
code and design notes live on branch `routing-module`.

## 7. Windows and Linux

Paths are written with `Path.as_posix()` and double-quoted. `claude` is found with `shutil.which`
(so it matches `claude.cmd`); a subprocess is always a list, never `shell=True`. Skip lists: POSIX
`.git node_modules venv .venv __pycache__ .cache .npm .cargo Library .Trash Pictures Movies Music`; Windows adds `AppData
OneDrive $Recycle.Bin`; symlinks and reparse points skipped; hard cap 200,000 directories
with a live counter; the Scan step names every root it skipped. **The depth cap of 6 bounds the
search for heads, not the walk**: a head must lie within 6 levels of the scan root to be found, but
once one is found its tree is walked to any depth, so a subtree nine or more levels down is
discovered with it. The skip list and the directory cap still apply inside a found tree, so a
project's own `node_modules`, `.venv` or `.claude/worktrees` are skipped however deep it goes.
Session-dir encoding is lossy
(`/`, `.`, `_` → `-`): always encode forward from the real path and match against the listing, never
decode. `.md` written with `newline="\n"`; block-strip tolerates CRLF. The terminal UI's subtree
connectors are box-drawing characters, so `wizard/terminal.py` test-encodes them against
`sys.stdout.encoding` once and falls back to ASCII of the same widths (`|--`, `` `-- ``, `|   `)
when they do not fit — a Windows console's default code page has none of them, and one
`UnicodeEncodeError` on a print would end the install. On Linux without
`DISPLAY`/`WAYLAND_DISPLAY`, or under WSL, go straight to the terminal UI; the URL is always printed.

## 8. Tests and CI

`tests/` mirrors `src/`; `fixtures/forest/` is a fake HOME with: `alpha/CLAUDE.md`, `alpha/sub/CLAUDE.md`,
`alpha/node_modules/pkg/CLAUDE.md` (must be skipped), `beta/CLAUDE.md`, `beta/.venv/lib/CLAUDE.md`,
`gamma/README.md` (no CLAUDE.md), `.Trash/old/CLAUDE.md`, `dot-claude/CLAUDE.md`,
and `dot-claude/projects/<encoded alpha>/<uuid>.jsonl`. `fixtures/claude_fake/claude`
(+ `claude.cmd`): a Python program that emits a real `--output-format json` envelope and switches on
`KIT_FAKE_MODE=ok|slow|garbage|authfail|nonzero|noschema`. `conftest.py` puts it first on PATH and
points HOME at a copy of the forest. CI matrix: ubuntu/macos/windows × Python 3.9 and 3.13: ruff check,
ruff format --check, pytest -q, `tools/bundle.py --check`, `dist/install.py --dry-run --no-browser
--root fixtures/forest`. `--root <dir>` is a documented testing flag.

## 9. Decisions taken (do not re-open)

**2026-09-22, Niv: the routing module is OUT of this kit.** SELF/DELEGATE routing and its three hooks
are a token-economy concern inside one project, not inter-project communication; shipping a hook that
denies tool calls under the article's name was wrong. The code lives on branch `routing-module`
(frozen at the last green main) for a possible second kit. v0.1 installs the laws module only; the
wizard has no Modules step; `settings.json` is never touched; `--modules` is gone.

zipapp bundle named `install.py` (README: download then run). Head-call model fixed to sonnet, not
user-selectable in v0.1.
