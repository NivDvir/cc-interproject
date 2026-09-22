# six-laws-kit

An installer that applies the six-law setup for running several Claude Code projects on one
machine as a system, as described in the article "The Six Laws for Running Claude Code Projects
as a System." It is for anyone running more than one Claude Code project on the same machine who
wants those projects to follow a shared ownership and communication protocol. It writes the
protocol files, lets each chosen project answer for itself, and can add an optional set of hooks
that enforce a delegation-routing policy. It does not write the article's content for you, does
not touch anything outside your home directory, and does not run automatically after install:
you run it once, review what it will do, and confirm.

## What you get

Under `~/.claude`, the installer can create or update:

- `SIX_LAWS.md`, `PROJECT_REGISTRY.md`, `INTERPROJECT_PROTOCOL.md`, `PRIOR_ART.md`,
  `DISPATCHER_QUEUE.md`
- one pointer line appended to `~/.claude/CLAUDE.md`
- a manifest, `~/.claude/six-laws.manifest.json`, recording everything it wrote
- (routing module) hooks under `~/.claude/hooks/six-laws/`, state files under
  `~/.claude/six-laws-state/`, and an entry merge into `~/.claude/settings.json`
- backups under `~/.claude/six-laws-backups/` of any file it changed

For each project you choose, it appends one marked block to that project's own `CLAUDE.md`: a
pointer to `~/.claude/SIX_LAWS.md`, and a note to rewrite its registry row in its own words on its
next session if the row was written by the installer.

The routing module is optional and off by default when it detects hooks that already serve the
same purpose. It installs three standalone hook programs:

- `packet_reminder.py` (`UserPromptSubmit`): reminds the session of last turn's tool-call tally.
- `labor_tally.py` (`Stop`): records what the session did in the turn just finished.
- `load_cap.py` (`PreToolUse`): counts direct context-loading tool calls in a turn and can deny
  the seventh one if nothing was delegated.

That last hook can deny a tool call. To turn it off, run `install.py --uninstall`, or open
`~/.claude/settings.json` and remove the three hook entries whose commands run `packet_reminder.py`,
`labor_tally.py`, and `load_cap.py`.

## Requirements

- Python 3.9 or later.
- The `claude` CLI installed and logged in. The installer checks this first and stops with a
  plain message if it is missing or not logged in.
- macOS, Linux, or Windows. On Windows, install Python from python.org; the installer uses the
  `py` launcher.

## Install

Download and run:

```
curl -fsSL https://github.com/NivDvir/six-laws-kit/releases/latest/download/install.py -o install.py
python3 install.py
```

On Windows: `py -3 install.py`.

`install.py` is a zip archive that Python runs directly. You can list its contents without
running it: `unzip -l install.py`.

Or clone the source and run it from there:

```
git clone https://github.com/NivDvir/six-laws-kit
cd six-laws-kit
PYTHONPATH=src python3 -m six_laws_kit
```

## What happens

The installer opens a local wizard (browser, or the terminal if no browser is available), with
seven steps:

1. **Welcome**: what the installer will do, and the cost note below.
2. **Scan**: finds every Claude Code project under your home directory (or `--root`), shown as a
   tree with a checkbox per project; picking a project also picks its subtrees.
3. **Modules**: choose `laws` (always installed) and the optional `routing` module.
4. **Register heads**: for each chosen project, asks its own `CLAUDE.md` for a short registry
   row, with live per-project progress.
5. **Review**: shows the exact file diff for everything that would be written. Nothing is
   written yet.
6. **Install**: writes the files you confirmed.
7. **Done**: shows the one text block you still need to paste yourself, and the uninstall
   command.

Cost note: registering heads makes one short `claude` call per chosen project, on your own
account, model `sonnet`, capped at 6 turns and $0.25 each.

## How each project writes its own row

A project's row in `PROJECT_REGISTRY.md` is marked `written-by: self` when that project's own
`CLAUDE.md` answered the registration call, or `written-by: installer` when it did not respond
and the installer wrote a fallback row from the file's heading and first paragraph. An
`installer` row is a placeholder, not the project speaking for itself; the project is expected to
rewrite it as `self` the next time it runs a Claude Code session there.

## The one manual step

The account-level Instructions box (Settings → Account → Instructions for Claude) can only be
written by you signed into your own account; nothing running on your machine can do it for you.
The Done step of the wizard gives you the exact text to paste there.

## Commands

- `--dry-run`: run the wizard through Review and print the plan; write nothing.
- `--status`: report what is currently installed, per project.
- `--uninstall`: remove what a previous install wrote.
- `--uninstall --restore-backups`: also restore any file the installer backed up.
- `--no-browser`: skip the browser wizard and use the terminal instead.
- `--modules laws`: install only the `laws` module (routing is on by default).
- `--root DIR`: scan a directory other than your home directory (for testing).
- `--version`: print the installed version.

Exit codes:

| Code | Meaning |
|---|---|
| 0 | ok |
| 2 | bad arguments |
| 3 | the `claude` CLI was not found |
| 4 | `claude` is not logged in |
| 5 | an error occurred while writing files |
| 6 | aborted (Ctrl-C, or "no" at a confirmation) |

## Uninstall

`--uninstall` reads `~/.claude/six-laws.manifest.json` and undoes exactly what it lists: it
deletes files the installer created, strips the marked blocks it inserted, and removes the hook
entries it added to `settings.json`. Backups it made along the way are left on disk under
`~/.claude/six-laws-backups/` unless you pass `--restore-backups`; either way, the path is
printed so you know where they are.

## Privacy and security

See `PRIVACY.md`: registering a project's head sends that project's `CLAUDE.md` to Anthropic
under your own `claude` account, the same as any other use of the CLI; the installer itself has
no telemetry and sends nothing to its author.

See `SECURITY.md`: the installer writes only under your home directory, does not run as root, and
serves its local wizard page only on `127.0.0.1` with a per-run token.

## Feedback

Open a GitHub issue using the bug report template. Include the full output of
`install.py --status`: that is the evidence the template asks for. Write issues in English.

## Licence

MIT. See `LICENSE`.
