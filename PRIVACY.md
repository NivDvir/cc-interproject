# Privacy

For each project you choose during the wizard, the installer runs `claude -p` once,
inside that project's directory. That call sends the project's `CLAUDE.md` content to
Anthropic, under your own logged-in Claude account, the same as any other use of the
`claude` CLI.

Nothing is sent to the author of this kit. The installer has no telemetry, no analytics,
and no update checks.

The manifest (`~/.claude/six-laws.manifest.json`) and the backups the installer takes
stay on your machine. They are never uploaded or shared.
