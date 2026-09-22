# hooks/

Three standalone Claude Code hook programs, installed as `~/.claude/hooks/six-laws/*.py` and
registered in `settings.json` (`write/settings.py`). State lives in
`~/.claude/six-laws-state/`, keyed by a sanitised session id
(`re.sub(r"[^A-Za-z0-9._-]", "_", sid)[:128]`).

## Files

| file | event | stdin | stdout | state files |
|---|---|---|---|---|
| `packet_reminder.py` | UserPromptSubmit | `{session_id, cwd, prompt}` | `additionalContext` = last turn's tally + `PACKET_REMINDER.md`, or nothing if both are empty | reads+deletes `head-tally.<sid>`; writes `turn-loads.<sid>` = `"0 6"`; deletes `turn-delegated.<sid>` |
| `labor_tally.py` | Stop | `{session_id, transcript_path}` | nothing | writes `head-tally.<sid>` e.g. `Read×7 Bash×3 Delegate×1`; reaps state files older than 1 day |
| `load_cap.py` | PreToolUse | `{session_id, tool_name, tool_input}` | allow = silent exit 0; deny = `permissionDecision` JSON | increments `turn-loads.<sid>` (`"<count> <threshold>"`); `turn-delegated.<sid>` switches the cap off |

## Contract

Each file reads one JSON object from stdin, never raises (the module body runs inside
`try/except BaseException` under `if __name__ == "__main__":`), and always exits 0. A missing or
empty `session_id` means do nothing and exit 0 — no state directory is even created.

## Invariants (kept verbatim from the bash originals this replaces)

1. **Worker discriminator.** `packet_reminder.py` creates `turn-loads.<sid>` at the start of every
   HEAD turn. UserPromptSubmit never fires for a sub-agent worker, so that file never exists for
   one. `load_cap.py` treats "no file" as "this is a worker" and allows silently, uncounted —
   workers are never capped.
2. **Silent allow.** `load_cap.py` prints JSON only on deny. Printing `permissionDecision: allow`
   would bypass the user's own permission rules (e.g. a `Bash(git push --force:*)` deny rule); an
   allow that has no decision to report is exit 0 with empty stdout.
3. **Threshold raise.** Every deny raises the stored threshold by `THRESHOLD_STEP` (6) so the same
   call is never denied twice in a row — the head acknowledges once (by dispatching a packet or
   stating why the step is SELF) and can then proceed.
4. **Exit 0 always.** No hook may fail a turn. Every code path — success, a corrupt state file, an
   unreadable transcript, a malformed JSON line, an exception nobody anticipated — ends in exit 0.
   `load_cap.py`'s counter parsing is fail-open: an unparsable `"<count> <threshold>"` line resets
   to `0 6` and processing continues, it does not deny.

## Why no shared module

Each file above is copied ALONE into `~/.claude/hooks/six-laws/` on a reader's machine and
invoked as `python3 <file>` (or `py -3 <file>` on Windows). None of them import
`six_laws_kit`, `run_state`, `paths`, or each other — a shared helper module would have to be
copied too, and installed hooks must keep working even if the rest of the kit's source tree is
gone. The small amount of duplication between the three files (session-id sanitising, the state
directory path, the delegation-tool test) is the cost of that independence, not an oversight.
