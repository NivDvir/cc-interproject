Inter-project constitution: read ~/.claude/INTERPROJECT_LAWS.md before any cross-project work (installed by cc-interproject).

---

The files under `~/.claude` are the authority for how the Claude Code projects on this machine work
together: `INTERPROJECT_LAWS.md`, `PROJECT_REGISTRY.md`, `INTERPROJECT_PROTOCOL.md`, `PRIOR_ART.md`, and
`DISPATCHER_QUEUE.md`.

A chat or Cowork session cannot read these files directly. Before doing any work that touches more
than one project — or before ruling on which project owns something — spawn a task that reads them
first, and act on what it finds.

The absence of the protocol from your context is not evidence that no protocol applies.
