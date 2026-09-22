# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
