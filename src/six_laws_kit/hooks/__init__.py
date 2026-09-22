"""Three standalone Claude Code hook programs (packet_reminder, labor_tally, load_cap).

Each file in this package is copied ALONE to `~/.claude/hooks/six-laws/` and registered as
`python3 <file>`. None of them import this package, `run_state`, `paths`, or each other — see
`ARCHITECTURE.md` for why. This `__init__.py` exists only so the package mirrors under `tests/`.
"""

from __future__ import annotations
