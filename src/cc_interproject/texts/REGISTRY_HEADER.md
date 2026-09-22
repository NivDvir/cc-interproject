# Project registry — the roster of heads

This is the shared registry Law 1 refers to: a "yellow pages" for every Claude Code project on this
machine — what each owns, and what each has asked others to watch for it. Read it before any
cross-project work. Keep your own row true; never write another project's row.

Every row carries who wrote it, because that decides how much weight it carries:

- **`written-by: self`** — the project wrote this about itself. Authoritative.
- **`written-by: installer`** — this kit wrote a placeholder row from the project's `CLAUDE.md`
  because no session answered when installed. Usable, not authoritative. The project replaces the
  placeholder with its own words the next time it runs; the label then records who wrote the
  current text, `self`. A placeholder row that a project never replaces stays usable; it is simply
  not authoritative.

## Columns

| Column | Meaning |
|---|---|
| Project | The project's name. |
| Path | Its directory. |
| Owns | What domain it is the head of. |
| Asks others to watch for | Signals or subjects it wants other projects to flag for it. |
| Contact subject | How another project should name a request when addressing this one. |
| Written by | `self` or `installer` — see above. |
| Updated | The date this row was last written. |
