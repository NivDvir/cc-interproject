# Security

## What the installer touches

The installer writes only under `$HOME`. It never touches a path outside it, and it never
runs as root or calls `sudo`.

Under `~/.claude`, it can create or update:

- `SIX_LAWS.md`, `PROJECT_REGISTRY.md`, `INTERPROJECT_PROTOCOL.md`, `PRIOR_ART.md`,
  `DISPATCHER_QUEUE.md`
- one pointer line appended to `~/.claude/CLAUDE.md`
- hooks under `~/.claude/hooks/six-laws/`
- state files under `~/.claude/six-laws-state/`
- backups under `~/.claude/six-laws-backups/`
- a manifest, `~/.claude/six-laws.manifest.json`
- an optional merge into `~/.claude/settings.json`, adding hook entries only

For each project the user chooses, it appends one marked block to that project's own
`CLAUDE.md`. It never edits any other part of a chosen project.

## What it does not touch

Nothing outside `$HOME`. No system files, no other users' files, no shell profile, no
crontab, no LaunchAgents.

## Network

The installer has no network calls of its own. The only network traffic it causes is the
`claude` CLI's own calls, made under the user's own logged-in account, once per chosen
project. See `PRIVACY.md` for what that call sends.

The local wizard page is served by a small HTTP server bound to `127.0.0.1` on a random
free port, with a per-run token required on every request. It is not reachable from
another machine.

## Reporting a vulnerability

Please open a private security advisory on this repository's GitHub page (Security tab →
Report a vulnerability) rather than a public issue. We will respond as soon as we can.
