# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-09-22

First release. Installs the inter-project laws, registry, protocol and vocabulary files; each
chosen project's own head writes its registry row at install time. Verified against the real
Claude Code CLI in a disposable cloud sandbox (five runs; see `docs/STAGING.md`). Known limitation:
the later self-replacement path for a fallback `installer` row is exercised by the offline harness
only — see the README's "How each project writes its own row" section.

## [Unreleased]

### Changed

- Renamed from six-laws-kit to cc-interproject ("Claude Code Inter-Project Communication").
  The number of laws no longer appears in any name, because the laws may change. The installed
  law file is now `~/.claude/INTERPROJECT_LAWS.md`, the manifest `interproject.manifest.json`,
  the backups directory `interproject-backups`, and the block markers `<!-- cc-interproject:begin
  id=... -->`. The Python package is `cc_interproject`.

### Removed

- Removed: the routing module (SELF/DELEGATE policy and hooks); kept on branch routing-module for a possible separate kit.

### Added

- Project scaffolding: license, tooling config, security and privacy notes.
