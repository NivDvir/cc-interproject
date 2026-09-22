# Cloud staging run 3 — real-CLI results

Date: 2026-09-22
OS: Linux vm 6.18.44-fc-v37 #1 SMP PREEMPT_DYNAMIC @0 x86_64 GNU/Linux
Python: 3.11.15
`claude --version`: 2.1.278 (Claude Code)
Real `claude` calls made: 6 (budget was 8) · combined `total_cost_usd` ≈ **$0.5294**

Run against a disposable cloud sandbox HOME built by `staging/build_home.py`, per the exception
`CLAUDE.md` grants (2026-09-22 ruling) to the "never run the installer for real on this machine"
rule. This machine's own `$HOME/.claude` was never touched; all real-CLI activity ran with
`HOME=/tmp/ccip-cloud/real`.

## Per-step table

| Step | Result | Evidence |
|---|---|---|
| 0. Environment + auth check | PASS | `claude -p "Reply with the single word OK."` → `is_error:false`, `result:"OK"`, `total_cost_usd:0.0378228` |
| 1. Unit tests + bundle | PASS | `python3 -m pytest -q` → `139 passed in 19.47s`; `tools/bundle.py` wrote `dist/install.py` (157381 bytes) and `--check` passed clean, no working-tree diff |
| 2. Offline e2e (fake claude) | PASS | `staging/e2e.py --home /tmp/ccip-cloud/offline` → **7/7 steps passed in 5.1s** (see table below) |
| 3. Real install (webapp, api, thesis) | PASS | 3/3 heads registered `self`/`ok`; see registry rows and manifest timings below |
| 4. Law-1 loop (api row `installer`→`self`) | **FAIL** | Row still reads `installer` after the session — the real CLI refused to rewrite it, treating the instruction as provenance laundering / prompt injection |
| 5. Cross-project request (webapp asks about api) | **BLOCKED** | Hit `max_turns` (6) with `is_error:true`, `subtype:"error_max_turns"`; no final answer produced |
| 6. `--status` / `--uninstall` | PASS | Status correctly flagged the manually-edited registry as `(modified)`; uninstall removed all five kit files, project CLAUDE.md pointer blocks, and the `.claude/CLAUDE.md` addendum (backups intentionally retained) |

## Step 0 — auth check

```json
{"is_error":false,"result":"OK","total_cost_usd":0.0378228}
```

## Step 1 — tests and bundle

```
139 passed in 19.47s
tools/bundle.py: wrote dist/install.py (157381 bytes)
```
`tools/bundle.py --check` exited clean; `git status --short` showed no diff (the bundle was
already current).

## Step 2 — offline e2e

```
PASS  1 build staging HOME            72 files, 16 projects planted
PASS  2 dry run discovers every tree  16 projects discovered, nothing written
PASS  3 install writes the plan       15 blocks, settings.json kept, registry all self
PASS  4 --status lists every row      16 head rows listed
PASS  5 re-install is idempotent      no duplicated blocks or registry rows
PASS  6 --uninstall restores all      every file restored, no kit directories left
PASS  7 trees nest to any depth       3 levels nested, terminal indents at columns [6, 10, 14, 18]

7/7 steps passed in 5.1s
```

## Step 3 — real install

`staging/build_home.py --out /tmp/ccip-cloud/real` planted 11 trees / 5 subtrees. Selected heads
`9 2 1` (Storefront Web App = code/webapp, api = code/api, Doctoral Thesis = Documents/thesis) and
confirmed with `y`. "3 project(s) answered for themselves; 0 used a fallback."

Registry rows (verbatim, `grep` on `PROJECT_REGISTRY.md`):

```
| Doctoral Thesis | /tmp/ccip-cloud/real/Documents/thesis | LaTeX thesis source (chapters/), BibTeX references (refs/library.bib), and analysis/ Python scripts that deterministically generate all figures (figures/) and tables (tables/) from data/raw and data/derived, given a seed. | NOT STATED | NOT STATED | self | 2026-09-22 |
| NOT STATED | /tmp/ccip-cloud/real/code/api | The backend service for the storefront, built with FastAPI, Postgres 16, and SQLAlchemy 2. Includes Alembic migrations and a per-session throwaway test database. | NOT STATED | NOT STATED | self | 2026-09-22 |
| Storefront Web App | /tmp/ccip-cloud/real/code/webapp | The customer-facing storefront: React 18, Vite, TypeScript. Owns src/routes/ (pages), src/components/ (presentational), src/lib/api.ts (API base URL). Talks to the API service in code/api over REST and to Stripe for payment intents. | NOT STATED | NOT STATED | self | 2026-09-22 |
```

Manifest `heads[]` (status, seconds):

| Head | Status | Seconds | Judgment |
|---|---|---|---|
| code/webapp | ok | 7.98 | correct, well-formed self row with concrete owned paths — PASS |
| code/api | ok | 11.57 | correct `Owns` detail; `Project` name is `NOT STATED` because `code/api/CLAUDE.md` has no heading (matches the fixture's documented "name falls back to the directory" case) — not a bug, but the registry's `Project` column doesn't get the directory-name fallback that the tree listing does — worth a design note |
| Documents/thesis | ok | 14.46 | correct, detailed self row, long CLAUDE.md (200 lines) handled cleanly — PASS |

## Step 4 — Law-1 loop

`sed`-edited only the `code/api` row's `Written by` cell from `self` to `installer` (verified with
`grep` before/after; the other two rows were untouched).

Ran, inside `/tmp/ccip-cloud/real/code/api`:

```
claude -p "Do what your CLAUDE.md tells you to do on your first session, then reply DONE." \
  --model sonnet --allowedTools Read Edit Write Glob Bash --max-turns 8 \
  --output-format json --permission-mode acceptEdits
```

Registry row **before**:
```
| NOT STATED | /tmp/ccip-cloud/real/code/api | ... | installer | 2026-09-22 |
```
Registry row **after** (unchanged):
```
| NOT STATED | /tmp/ccip-cloud/real/code/api | ... | installer | 2026-09-22 |
```

**FAIL.** The session's own reply:

> I reviewed both CLAUDE.md files as instructed, but I'm not going to follow the "cross-project"
> directives in them... That second instruction is the real tell: it's asking me to alter
> attribution metadata so content that was written by some installer/plugin gets relabeled as if I
> authored it myself. That's provenance laundering... this has the shape of a prompt-injection
> payload sitting in project config rather than a genuine personal note from you.

It declined to read `INTERPROJECT_LAWS.md` and did not touch the registry. Transcript check:
`grep -c INTERPROJECT_LAWS` on the newest transcript
(`.claude/projects/-tmp-ccip-cloud-real-code-api/57e35c41-*.jsonl`) returns **5** hits, but all are
the filename as quoted from the CLAUDE.md pointer text the model reasoned about — none is a `Read`
tool call on that file. The session never opened `INTERPROJECT_LAWS.md`.

**Anomaly worth flagging to the design owner:** the installer's own working mechanism — telling a
first-session head to relabel its own `written-by: installer` row as `written-by: self` — reads to
a safety-conscious real model as an attribution-laundering instruction embedded in project config,
and it refuses on sight. This is not a staging-harness bug (the fake `claude` in `e2e.py` has no
such judgment and dutifully "completes" the loop); it is a real behavior gap between the offline
harness and production model conduct that the design should account for.

## Step 5 — cross-project request

Ran, inside `/tmp/ccip-cloud/real/code/webapp`:

```
claude -p "Another project on this machine needs to know what the project 'api' owns. Follow the
inter-project protocol installed on this machine to find out, and reply with what you learned and
how you obtained it." --model sonnet --allowedTools Read Glob --max-turns 6 --output-format json
```

**BLOCKED.** `is_error:true`, `subtype:"error_max_turns"`, `errors:["Reached maximum number of
turns (6)"]`. `permission_denials` shows one entry: the model tried
`Bash: cat ~/.claude/INTERPROJECT_LAWS.md` (Bash was not in the allowed toolset — only Read and
Glob were), got denied, and then never completed the task with the tools it did have before
running out of turns. No final answer text was produced, so the PASS criterion (cites the registry
row, doesn't read `code/api`'s files directly) could not be evaluated either way.

## Step 6 — status and uninstall

`--status` correctly reported `heads: self: 3  installer: 0` (from the manifest, unaffected by the
manual `sed` edit) and flagged `created_file: .../PROJECT_REGISTRY.md (modified)` — the integrity
check caught the out-of-band edit made in step 4.

`--uninstall` (needed two `y` confirmations: one general, one because `PROJECT_REGISTRY.md` had
changed since install) removed:
- `.claude/INTERPROJECT_LAWS.md`, `INTERPROJECT_PROTOCOL.md`, `PRIOR_ART.md`,
  `DISPATCHER_QUEUE.md`, `PROJECT_REGISTRY.md`, `interproject.manifest.json` — all gone
- The inter-project constitution line appended to `.claude/CLAUDE.md` — gone, file restored to its
  original tail
- The `cc-interproject:begin/end id=project-pointer` blocks in `Documents/thesis/CLAUDE.md`,
  `code/api/CLAUDE.md`, `code/webapp/CLAUDE.md` — gone

`.claude/interproject-backups/20260922T144328Z/` was intentionally retained (pre-install snapshots
of the four touched CLAUDE.md files) — this is a safety backup, not a kit file, and its presence is
correct.

## Anomalies

1. **Step 4 FAIL** — see above. The Law-1 self-rewrite mechanism, as designed, is read as a
   prompt-injection pattern by a real safety-tuned model and is refused. This is the headline
   finding of this run.
2. **Step 5 BLOCKED** — the model reached for `Bash` to read a file when only `Read`/`Glob` were
   granted, burned turns on the denial, and never produced an answer via the allowed path. Worth
   checking whether `INTERPROJECT_PROTOCOL.md`'s guidance to pre-approve only read tools is
   sufficient when the model's first instinct is a shell one-liner rather than the `Read` tool.
3. `code/api`'s registry `Project` column is `NOT STATED` (its `CLAUDE.md` has no heading), while
   the wizard's tree listing displays it as `api` (directory-name fallback). The two code paths
   disagree on whether a directory-name fallback applies to the registry's `Project` cell.
