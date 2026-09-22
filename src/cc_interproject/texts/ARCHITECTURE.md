# texts/

These files are data, not code: the public-text bodies the installer writes into a reader's
`~/.claude/` and into the projects they choose. Nothing here imports or executes; `loader.py` is
the one piece of code, and it only reads.

## Version line

Each `.md` file opens with `<!-- cc-interproject text v<N> -->` (`INTERPROJECT_LAWS.md` also names its source
article). Bump `N` only when the file's meaning changes, not for wording fixes. `write/blocks.py`
records the version it inserted, so `--uninstall` can tell a stale block from a current one.

## Who may edit

Every file here is public-facing text: it ships in a reader's own `~/.claude/` or project. It is
approved by the kit's owner before release, the same way the README and wizard copy are. `STYLE.md`
governs the prose.

## Loader contract

`loader.read(name)` returns one file's text by name; `loader.names()` lists what this package
ships, `ARCHITECTURE.md` and `loader.py` excluded. Both must work identically from the source tree
and from inside the built zipapp — see `loader.py`'s docstring.
