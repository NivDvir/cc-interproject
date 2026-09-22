# Legacy Order Tool

The internal order tool that predates the storefront. PHP 7.4 behind Apache, MySQL 5.7.
It is still the system of record for wholesale orders, so it cannot simply be deleted.

Only two things are allowed here: security fixes, and changes needed to keep the
wholesale export working. Everything else waits for the replacement.

<!-- six-laws-kit:begin id=project-pointer v=1 -->
This project is one head in a forest of Claude Code projects on this machine. Before any
cross-project work read `~/.claude/SIX_LAWS.md`, `~/.claude/PROJECT_REGISTRY.md`, and
`~/.claude/INTERPROJECT_PROTOCOL.md`.

If your row in the registry is marked `written-by: installer`, rewrite it in your own words as
`written-by: self` on this session, then continue with the user's task.

Reach other projects only through their heads; never edit their files.
<!-- six-laws-kit:end id=project-pointer -->

## Notes added after that block

The nightly export runs at 02:15 from cron on the application host. If it fails, the
warehouse sees yesterday's quantities and ships the wrong thing, so it is paged.

Test data lives in `sql/fixtures.sql`. Load it into a scratch database only; it contains
real customer names from before the anonymisation pass.
