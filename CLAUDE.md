# cc-interproject — subtree of ~/opportunity-radar

This directory is a **subtree of the `~/opportunity-radar` head**, not a head of its own. Its owner is
that project (ruling: `~/opportunity-radar/CLAUDE.md`, "The reader-facing kit is this project's",
2026-09-22). It has its own git repository because it is published to GitHub; the parent ignores it.

What it is: an installer that lets a reader of the article "The Six Laws for Running Claude Code
Projects as a System" apply the inter-project setup to the Claude Code projects on their own
machine.

Governing documents, in order: `docs/DESIGN.md` (architecture), `docs/INTERFACES.md` (every
cross-module signature and the HTTP API — workers build against this, never against each other's
code), `docs/STYLE.md` (the style contract), `../../publication/cc-interproject/SPEC.md` (the agreed
behaviour). Everything public-facing (README, texts/, wizard copy) is approved by Niv before it leaves.

Working rules inherited from the parent: `../../.claude/DELEGATION.md` and the parent `CLAUDE.md`.
Never run the installer for real on this machine from a session here; `--dry-run` only.
