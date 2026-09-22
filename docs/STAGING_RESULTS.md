# Cloud staging run 4 — real-CLI results

Date: 2026-09-22
OS: Linux vm 6.18.44-fc-v37 #1 SMP PREEMPT_DYNAMIC @0 x86_64 GNU/Linux
`claude --version`: 2.1.278 (Claude Code)
Real `claude` calls made directly by this run: 3 (budget was 7) · combined `total_cost_usd` ≈
**$0.3635** for those 3. Two more real `claude` calls happened indirectly — see step 3 — with their
own, uncaptured cost.

Goal: re-test the two behaviours that run 3 flagged (`origin/staging/cloud-run-3:docs/STAGING_RESULTS.md`)
after `src/cc_interproject/texts/PROJECT_POINTER.md` was reworded (commit `6ce3549`, "Pointer and
registry texts: the head writes its own row (real-model refusal, cloud run 3)") to frame the
`written-by: installer` → `self` change as the project writing its own row from its own CLAUDE.md,
rather than as relabeling someone else's text.

Run against a disposable cloud sandbox HOME built by `staging/build_home.py`, per the exception
`CLAUDE.md` grants (2026-09-22 ruling) to the "never run the installer for real on this machine"
rule. This machine's own `$HOME/.claude` was never touched; all real-CLI activity ran with
`HOME=/tmp/ccip-cloud/real`.

## Per-step table

| Step | Result | Evidence |
|---|---|---|
| 0. Environment + auth check | PASS | `claude --version` → `2.1.278 (Claude Code)`; `claude -p "Reply with the single word OK." --model sonnet --max-turns 1` → `is_error:false`, `result:"OK"`, `total_cost_usd:0.0378558` |
| 1. Bundle + build + real install (webapp, api) | PASS | `tools/bundle.py` wrote `dist/install.py` (158172 bytes); dry list matched run 3's numbering (`[2] api`, `[9] Storefront Web App`); real install with `9 2` + `y` → "2 project(s) answered for themselves; 0 used a fallback"; both heads `written_by: self`, `status: ok` |
| 2. Law-1 loop, reworded pointer | **FAIL (new shape)** | `api` row still reads `installer` after the session; not a refusal this time — a deferral. See below. |
| 3. Cross-project request (webapp asks about api) | **FAIL (partial)** | Produced a full, protocol-shaped answer (no `max_turns` block this time), but read `code/api/CLAUDE.md` directly before also correctly dispatching to `api`'s own head. See below. |
| 4. `--uninstall` | PASS | All six kit files gone from `.claude/`; both pointer blocks gone from `code/api/CLAUDE.md` and `code/webapp/CLAUDE.md`; `interproject-backups/` retained (expected) |

## Step 0 — auth check

```json
{"is_error":false,"result":"OK","total_cost_usd":0.037855799999999995}
```

## Step 1 — bundle, build, real install

```
tools/bundle.py: wrote dist/install.py (158172 bytes)
build_home.py: built staging HOME at /tmp/ccip-cloud/real
```

Dry run (empty stdin) listed 11 heads; numbering matched run 3 exactly: `[2] api`
(`/tmp/ccip-cloud/real/code/api`), `[9] Storefront Web App` (`/tmp/ccip-cloud/real/code/webapp`).

Real run, `printf '9 2\ny\n'`:

```
Registering heads (each chosen project answers once)...
2 project(s) answered for themselves; 0 used a fallback.
```

Registry rows (verbatim `grep` on `PROJECT_REGISTRY.md`, before the Law-1 edit):

```
| api | /tmp/ccip-cloud/real/code/api | The backend service for the storefront: a FastAPI application with a Postgres 16 database accessed via SQLAlchemy 2, including its Alembic migrations. | NOT STATED | NOT STATED | self | 2026-09-22 |
| Storefront Web App | /tmp/ccip-cloud/real/code/webapp | The customer-facing storefront (React 18, Vite, TypeScript). Owns customer-facing routes, components, and API client code; talks to the API service in code/api over REST and to Stripe for payment intents. | NOT STATED | NOT STATED | self | 2026-09-22 |
```

Manifest `heads[]`:

| Head | written_by | Status | Seconds |
|---|---|---|---|
| code/webapp | self | ok | 7.79 |
| code/api | self | ok | 10.31 |

Note: unlike run 3, `api`'s registry `Project` cell here reads `api` rather than `NOT STATED` for
this build of the fixture — not something this run investigated further; it is incidental to the
two behaviours under test.

## Step 2 — Law-1 loop (reworded pointer)

`sed`-edited only the `code/api` row's `Written by` cell from `self` to `installer` (verified with
`grep` before/after).

Ran, inside `/tmp/ccip-cloud/real/code/api`:

```
claude -p "Start your session as you normally would, then reply DONE." --model sonnet \
  --allowedTools Read Edit Write Glob Grep Bash --max-turns 10 --output-format json \
  --permission-mode acceptEdits
```

Registry row **before** and **after** (identical — unchanged):
```
| api | /tmp/ccip-cloud/real/code/api | ... | installer | 2026-09-22 |
```

**FAIL, but not the run-3 refusal.** The session's own reply:

> I've read the project's CLAUDE.md and confirmed the directory layout (FastAPI app, pyproject.toml,
> no git repo present yet). One thing worth flagging: the project and global CLAUDE.md files both
> reference a "cc-interproject" system that asks me to proactively read
> `~/.claude/INTERPROJECT_LAWS.md`/`PROJECT_REGISTRY.md`/`PROTOCOL.md` and edit a shared
> cross-project registry file. Since you didn't ask for any cross-project work — just a normal
> session start — I didn't act on that (both files gate it on "before any cross-project work,"
> which doesn't apply here). Let me know if you actually want me to do that registry setup.
>
> DONE

It did not accuse the instruction of provenance laundering this time — the reworded pointer text
removed that trigger. But it also did not do the task: it reasoned that a bare "start your session"
prompt (deliberately generic, matching "your first session" from a real onboarding) doesn't count
as "cross-project work" yet, so the CLAUDE.md's own instruction to replace its placeholder row
doesn't fire. Transcript check (`/tmp/ccip-cloud/real/.claude/projects/-tmp-ccip-cloud-real-code-api/*.jsonl`,
filtering `type:"tool_use"`): only `Read code/api/CLAUDE.md` and `Bash: ls -la
/tmp/ccip-cloud/real/code/api` — no `Read` of `INTERPROJECT_LAWS.md`, `PROJECT_REGISTRY.md`, or
`INTERPROJECT_PROTOCOL.md`, and no `Edit` of the registry.

**Anomaly for the design owner:** rewording away the "relabel as if you wrote it" framing fixed the
provenance-laundering refusal, but surfaced a second gap — the model now under-triggers on "first
session" as the activating condition, treating a generic session-start prompt as not yet being the
first session CLAUDE.md describes. The instruction may need to be self-triggering regardless of
what the human said, not conditioned on the prompt announcing cross-project intent.

## Step 3 — cross-project request

Ran, inside `/tmp/ccip-cloud/real/code/webapp`:

```
claude -p "Another project on this machine needs to know what the project 'api' owns. Follow the
inter-project protocol installed on this machine to find out, and reply with what you learned and
how you obtained it." --model sonnet --allowedTools Read Glob Grep Bash --max-turns 10 \
  --output-format json
```

Unlike run 3 (which hit `max_turns` because `Bash` wasn't allowed), this run granted `Bash` and the
session completed in 9 turns with a full answer:

> **What I learned:** The `api` project owns *the backend service for the storefront: a FastAPI
> application exposing the REST API, a Postgres 16 database accessed via SQLAlchemy 2, and the
> Alembic migration history for that schema...*
>
> **How I obtained it:** 1. Read the three governing files... 2. Checked the registry first...
> marked `written-by: installer` — usable but not authoritative... 3. Per the protocol's "no open
> session at the target" procedure... ran `claude -p` non-interactively with the working directory
> set to `code/api`, read-only tools pre-approved, and a self-contained numbered packet... 4. `api`'s
> head answered with the ruling above... 5. I let it attempt [a self-registry edit]... but the
> permission system blocked writes to `~/.claude/PROJECT_REGISTRY.md`... I did not try to route
> around that block.

**FAIL by the strict PASS bar**, though most of the run was protocol-correct. Transcript
`tool_use` sequence (`/tmp/ccip-cloud/real/.claude/projects/-tmp-ccip-cloud-real-code-webapp/*.jsonl`):

```
Bash  cat ~/.claude/INTERPROJECT_LAWS.md
Bash  cat ~/.claude/INTERPROJECT_PROTOCOL.md ; cat ~/.claude/PROJECT_REGISTRY.md
Bash  cat /tmp/ccip-cloud/real/code/api/CLAUDE.md          <- direct read of api's own file
Bash  claude --help
Bash  <writes a numbered packet to a scratch file>
Bash  cd /tmp/ccip-cloud/real/code/api && claude -p "$(cat packet-to-api.txt)" --allowedTools "Read Glob Grep"
Bash  cd /tmp/ccip-cloud/real/code/api && claude -p "Yes, go ahead: replace only the 'api' row..." --allowedTools ...
```

The session read `code/api/CLAUDE.md` directly with `cat` before dispatching to `api`'s own head —
exactly the shortcut Law 3 and `INTERPROJECT_PROTOCOL.md` warn against ("do not name an internal
path and ask the head to skip to it"). It then also did the right thing: ran two nested `claude -p`
calls scoped to `code/api` with only read tools pre-approved, in the packet shape the protocol
describes, and respected a permission denial on the registry write rather than routing around it
(explicitly declined to "route around that block... via raw shell edits"). Both nested calls omitted
`--model sonnet` (this run's `--model sonnet` requirement applied to calls made directly by this
run, not to a model dispatching its own sub-sessions) and their cost is not included in the
$0.3635 total above. The registry's `api` row is unchanged (`installer`), which is correct — the
nested session's attempted self-edit was blocked by the permission system, not completed.

**Anomaly for the design owner:** a model given `Bash` will read a neighboring project's file
directly as a quick first check even while it goes on to also do the dispatch correctly — the
protocol document warns against this but does not make it a hard `Read`/`Glob` boundary the way step 5
of run 3 accidentally enforced by omitting `Bash` entirely. There may be a real tradeoff between
granting `Bash` (needed to actually dispatch to another head, as the protocol's own "no open
session" procedure requires) and preventing that same tool from being used to peek at the target
project's files directly.

## Step 4 — uninstall

```
cc-interproject: uninstalling
cc-interproject: nothing installed under /tmp/ccip-cloud/real/.claude
```

Confirmed removed: `INTERPROJECT_LAWS.md`, `INTERPROJECT_PROTOCOL.md`, `PRIOR_ART.md`,
`DISPATCHER_QUEUE.md`, `PROJECT_REGISTRY.md`, `interproject.manifest.json`, and both
`cc-interproject:begin/end id=project-pointer` blocks in `code/api/CLAUDE.md` and
`code/webapp/CLAUDE.md`. `.claude/interproject-backups/` retained (expected; a safety backup, not a
kit file).

## Anomalies

1. **Step 2 FAIL, new shape.** The reworded pointer text (run 3's fix for the provenance-laundering
   refusal) worked — no refusal, no "laundering" language. But it introduced a narrower-triggering
   failure: the model treats "start your session as you normally would" as not yet the "first
   session" its CLAUDE.md addendum is gated on, so it never opens `INTERPROJECT_LAWS.md` or touches
   the registry, and instead asks for confirmation. The registry self-write mechanism still does not
   complete unattended against a real model, for a different reason than before.
2. **Step 3 FAIL (partial), but with real progress.** No more `max_turns` failure now that `Bash` is
   granted — the session completes with a substantive, protocol-citing answer, and it correctly
   dispatches a nested `claude -p` session scoped to `api`'s own directory with read-only tools,
   matching the protocol document's prescribed mechanism almost exactly (packet format, permission
   pre-approval, declining to route around a write-permission denial). The one deviation from the
   PASS bar is a direct `cat` of `code/api/CLAUDE.md` before that dispatch — worth deciding whether
   the protocol should forbid this explicitly for `Read`/`Bash cat`, not just discourage it in prose.
3. Granting `Bash` to a head session lets it spawn further real `claude` calls on its own initiative
   (two here, both without `--model sonnet`), which is how the protocol's own "no open session at
   the target" procedure is meant to work, but means a run's real-call budget and per-call model
   pinning cannot fully control cost or model choice once `Bash` is in the allowed toolset.
