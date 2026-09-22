# Style contract (binding on every file in this repo)

Source: the owner's charter `~/dev/reticle-access/docs/style/STYLE_NIV.md` and its `ruff.toml`.

- Files: warn at 400 lines, fail at 600. Functions: cyclomatic complexity ≤ 15, nesting ≤ 3 levels.
- Line length 110. Target Python 3.9 (no `match`, no `X | Y` in annotations at runtime; use
  `from __future__ import annotations`).
- Directories divide by essential category. Each category root has an `ARCHITECTURE.md`. No sideways
  imports between categories — a category may import only the package root modules `run_state` and
  `paths` (and the stdlib). `tests/test_architecture.py` enforces this. Named exceptions (from DESIGN §2): `write` may import
  `texts`; `write.apply` may import `manifest.record`; `manifest.uninstall` may import `write.blocks` and
  `write.settings`; `cli` and `wizard.api` may import every category.
- One owner per feature: the module that owns a feature holds all of its logic. No thin service
  layers, no interfaces / abstract classes / generics of our own. Layers only where a framework
  forces them.
- Tests mirror `src/six_laws_kit/` one to one under `tests/`. Fixtures live in `fixtures/` at the repo
  root, outside the test tree.
- Module docstring: purpose and usage in two or three prose sentences. `from __future__ import
  annotations` first. Constants in SCREAMING_SNAKE at the top of the file. CLI modules use argparse,
  `def main() -> int`, `raise SystemExit(main())`; exit codes documented in the docstring.
- Errors are handled narrowly at the point of I/O with a plain message on stderr; never a bare
  `except`. No `logging` module: `print(..., file=sys.stderr)` for diagnostics.
- Comments are few and explain why, never what. No commented-out code, no tombstones, no "TODO" left
  behind, no decorative banners.
- Naming: verbs for functions (`find_projects`, `render_page`), nouns for data. No abbreviations that a
  new reader would have to guess.
- The wizard's HTML, CSS, JS and SVG are real files under `wizard/assets/`. They are never embedded
  as strings in Python.
- Tooling: `ruff check` + `ruff format` (line 110, mccabe 15, rules E F W I N UP SIM RET PIE TRY BLE
  C901 T20 ERA; T20 exempt for `cli.py`, `wizard/terminal.py`, `hooks/*` which print by design),
  pre-commit, pytest.
- Public text (README, `texts/*.md`, wizard copy): plain English, short sentences, no superlatives,
  no emoji, no em-dash chains. Vale with the repo's `.vale.ini` if present.
