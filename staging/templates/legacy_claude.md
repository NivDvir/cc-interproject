# Legacy Order Tool

The internal order tool that predates the storefront. PHP 7.4 behind Apache, MySQL 5.7.
It is still the system of record for wholesale orders, so it cannot simply be deleted.

Only two things are allowed here: security fixes, and changes needed to keep the
wholesale export working. Everything else waits for the replacement.

<!-- cc-interproject:begin id=project-pointer v=1 -->
The owner of this machine installed Claude Code Inter-Project Communication (cc-interproject) and
chose to include this project in it. Before any cross-project work, read
`~/.claude/INTERPROJECT_LAWS.md`, `~/.claude/PROJECT_REGISTRY.md` and
`~/.claude/INTERPROJECT_PROTOCOL.md`.

The registry's rule is that each project describes itself. The installer may have left a
placeholder row for this project, marked `written-by: installer`. The owner asks you, once, to
replace that placeholder with a row you write yourself from this CLAUDE.md, and to mark it
`written-by: self` because you are then its author. Then continue with the user's task. Do not
edit other projects' rows or files; reach other projects only through their heads.
<!-- cc-interproject:end id=project-pointer -->

## Notes added after that block

The nightly export runs at 02:15 from cron on the application host. If it fails, the
warehouse sees yesterday's quantities and ships the wrong thing, so it is paged.

Test data lives in `sql/fixtures.sql`. Load it into a scratch database only; it contains
real customer names from before the anonymisation pass.
