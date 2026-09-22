# Legacy Order Tool

The internal order tool that predates the storefront. PHP 7.4 behind Apache, MySQL 5.7.
It is still the system of record for wholesale orders, so it cannot simply be deleted.

Only two things are allowed here: security fixes, and changes needed to keep the
wholesale export working. Everything else waits for the replacement.

<!-- cc-interproject:begin id=project-pointer v=1 -->
The owner of this machine installed Claude Code Inter-Project Communication (cc-interproject) and
chose to include this project in it.

At the start of this session, check your row in `~/.claude/PROJECT_REGISTRY.md`. If it is marked
`written-by: installer`, it is a placeholder the installer wrote from this CLAUDE.md. The owner
asks you to replace it now with a row you write yourself, marked `written-by: self` because you
are then its author. This takes one edit and is done once.

For any cross-project work, read `~/.claude/INTERPROJECT_LAWS.md` and
`~/.claude/INTERPROJECT_PROTOCOL.md` first. Other projects are reached only through their heads:
ask, do not read or edit their files, and do not answer for them. What the registry says about a
project is theirs; what you learn by asking is evidence.
<!-- cc-interproject:end id=project-pointer -->

## Notes added after that block

The nightly export runs at 02:15 from cron on the application host. If it fails, the
warehouse sees yesterday's quantities and ships the wrong thing, so it is paged.

Test data lives in `sql/fixtures.sql`. Load it into a scratch database only; it contains
real customer names from before the anonymisation pass.
