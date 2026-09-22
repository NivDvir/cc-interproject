# Global instructions

These are my own notes for every project on this machine. They are not part of any kit.

## How I like to work

- Read the project's own CLAUDE.md before touching anything.
- Prefer small commits with a one-line subject in the imperative mood.
- Never push to `main` directly; open a branch and a pull request instead.
- Run the test suite before you tell me something works.
- If a command needs credentials, stop and ask me to run it myself.

## Style

- Python: 4 spaces, type hints on public functions, no wildcard imports.
- JavaScript: 2 spaces, no default exports, prefer `const`.
- Keep lines under 100 characters where the language allows it.
- Comments explain why, not what.

## Tools

- `rg` is installed and is much faster than `grep -r`.
- `just` runs the task files in each repo; read the `justfile` before guessing.
- The database in `code/api` is Postgres 16, reachable on port 5433 in development.

## Things to avoid

- Do not add new dependencies without asking.
- Do not reformat a file you were not asked to touch.
- Do not write throwaway scripts into the repository root.

## Notes

I work across several unrelated projects in one week, so context from one is rarely
useful in another. Ask when something looks like it belongs to a different repository.
