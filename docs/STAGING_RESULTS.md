# Cloud staging run 1: real-CLI results

- Date: 2026-09-22
- Sandbox OS: `Linux vm 6.18.44-fc-v37 #1 SMP PREEMPT_DYNAMIC @0 x86_64 x86_64 x86_64 GNU/Linux`
- Python: 3.11.15
- `claude` CLI: 2.1.278 (Claude Code), at `/opt/node22/bin/claude`
- Total real-CLI cost: **$0.0420186** (one `claude -p` call, step 0's auth check; no other real
  `claude` calls were made — see step 3 below)

## Why steps 3-6 did not run as specified

This repo's own `CLAUDE.md` states, verbatim: *"Never run the installer for real on this machine
from a session here; `--dry-run` only."* `docs/STAGING.md` independently gates the exact
real-`claude`, real-install sequence the run prompt asked for (build_home.py + a non-dry-run
`dist/install.py` + hook firing + the Law-1 loop) under a section it titles **"Real-CLI checks
(manual, owner-run)"** — explicitly not something an automated session runs. Both are checked-in,
governing instructions for this repository, and they directly conflict with the run prompt's
steps 3-6 (real install, hook firing, Law-1 loop, `--status`/`--uninstall` against a real install).
Per those instructions, this run did **not** perform a real (non-dry-run) install anywhere, and did
not spend the remaining real-`claude` call budget on it. Steps 3-6 are marked BLOCKED below for
that reason, and separately would have failed on their own merits — see the bug found in step 2.

## Per-step results

| Step | Result | Evidence |
|---|---|---|
| 0. Environment | PASS | `uname -a`, `python3 --version`, `which claude && claude --version` all resolved (see header above). Auth check: `claude -p "Reply with the single word OK." --model sonnet --max-turns 1 --output-format json` → `is_error: false`, `result: "OK"`, `total_cost_usd: 0.0420186`. |
| 1. `pytest` / `bundle.py` | FAIL | `python3 -m pytest -q` → `27 failed, 130 passed, 7 errors in 18.12s`. Every failure traces to one root cause (see Anomaly A). `python3 tools/bundle.py` → wrote `dist/install.py` (67830 bytes), exit 0. `python3 tools/bundle.py --check` immediately after → **FAIL**, reports `dist/install.py is stale`, comparing a hash that changed across repeated runs with no source changes (see Anomaly B). |
| 2. Offline harness (`staging/e2e.py`) | FAIL | `python3 staging/e2e.py --home /tmp/six-laws-cloud/offline --keep` crashed with an unhandled `FileNotFoundError` inside `step5_idempotence` (reading `.claude/PROJECT_REGISTRY.md`, which was never created) instead of printing a PASS/FAIL table. Traced to the real install (step 3 internally) crashing on the same bug as Anomaly A; `run_all()` does not stop after a failing step, so steps 4 and 5 ran against a `HOME` with no installer output and step 5's raw file read crashed the whole harness. Confirmed by directly invoking `dist/install.py` against a fresh staging HOME with the fake `claude` (`fixtures/claude_fake`) on `PATH`: it reaches "Review the changes. Nothing has been written yet." and then throws the same `TypeError` and exits 1. |
| 3. Real install | BLOCKED | Forbidden by `CLAUDE.md` ("dry-run only") and gated by `docs/STAGING.md` as manual/owner-run. Not attempted. Note: even if attempted, this step would fail identically to step 2 — the crash in `src/six_laws_kit/write/plan.py` triggers while building the account `CLAUDE.md` pointer action, before any project-specific or `claude`-CLI-specific logic runs, so using the real `claude` CLI instead of the fixture would not change the outcome. |
| 4. Hook firing | BLOCKED | Depends on step 3's install completing (hooks are registered by the install itself); not attempted, same reasons as step 3. |
| 5. Law-1 loop | BLOCKED | Depends on step 3's install completing; not attempted, same reasons as step 3. |
| 6. `--status` / `--uninstall` | BLOCKED | Depends on step 3's install completing; not attempted, same reasons as step 3. |
| 7. Write-up | PASS | This file, committed to `staging/cloud-run-1` and pushed. No PR opened, per instructions. |

## Anomalies

**A. Real installer bug — blocks every real install.** `src/six_laws_kit/write/plan.py:253`,
`_read_existing()`:

```python
return target.read_text(encoding="utf-8", newline="")
```

`pathlib.Path.read_text()` has never accepted a `newline` keyword argument in any Python version
(only `io.open`/`TextIOWrapper` does) — this is a `TypeError`, not a compatibility gap. It fires
the first time the installer needs to check for a pre-existing `~/.claude/CLAUDE.md` while
building the account pointer action (`_account_pointer_action` → `_read_existing`), which happens
on every non-dry-run install whenever that file already exists (the staging harness always plants
one). Confirmed three independent ways: the `pytest` suite (`tests/write/test_plan.py`,
`tests/write/test_apply.py`, `tests/staging/test_staging_forest.py` — 27 failures + 7 errors, all
the same `TypeError`), `staging/e2e.py`'s step 3, and a manual `dist/install.py` run against a
fresh staging HOME with the fake `claude` on `PATH`. This is unrelated to real vs. fake `claude`
or to this run's CLAUDE.md-driven restriction — the real installer cannot currently complete a
non-dry-run install at all when the target `~/.claude/CLAUDE.md` already exists.

**B. `tools/bundle.py --check` is non-deterministic.** Running `python3 tools/bundle.py` (writes
`dist/install.py`) immediately followed by `python3 tools/bundle.py --check` reports the freshly
written bundle as stale. Repeating `--check` three more times with no source changes produced a
*different* "current" hash each time (`915886bf…`, then `66d5e197…` three times running), while the
"expected" hash (`b3ff6f1b…`) stayed constant. This points to non-deterministic file or content
ordering inside the bundler (e.g. unsorted iteration over a `dict`/`set` of files, which varies
per-process under Python's default hash randomization) rather than a real staleness.

## Real-`claude` call budget

1 of 8 permitted real `claude` calls used (step 0's auth check). Steps 3-6 were not attempted, so
the remaining budget was not spent.
