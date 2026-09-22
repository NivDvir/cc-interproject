# Staging harness

`staging/` builds a throwaway HOME that looks like a real user's machine and runs the bundled
installer against it with the fake `claude` from `fixtures/claude_fake`; this machine's own
`~/.claude` is never touched. `fixtures/forest` proves single behaviours, this proves they hold
together on a messy one.

Seven steps run in order: build, dry run, install, `--status`, re-install, `--uninstall`, and a
last one that reads the forest back. Step 7 lives in `staging/tree_shape.py`: it imports the kit
from the bundle under test, runs the wizard's own Scan step over the staging HOME, and checks two
things about `code/platform` — that `GET /api/state`'s tree JSON nests three levels of subtree
under the one head, and that `wizard/terminal.py` prints all four names with each indented further
than the one above it.

## What the cases model

| Case | Models | Why it is here |
|---|---|---|
| `code/webapp` | Node, `.git/`, a vendored dependency tree holding a CLAUDE.md | the common project, and the common decoy |
| `code/api` | Python, `.venv/.../site-packages/CLAUDE.md`, own CLAUDE.md with no heading | the name falls back to the directory |
| `code/monorepo` | root plus two package CLAUDE.md files, plus `.claude/worktrees/` | subtrees nest under their root; a worktree copy is not a project |
| `Documents/thesis` | 200 lines, headings, tables, code fences | a long file survives the append unchanged |
| `code/ml-lab` | UTF-8 BOM and CRLF | a Windows-authored file must keep its bytes |
| `code/dotfiles` | empty (0 byte) CLAUDE.md | an empty project still earns a registry row |
| `Projects/Client Work/acme site` | spaces in the path, French prose | quoting, and non-ASCII left alone |
| `code/legacy` | an existing kit block with text after it | idempotence: still one block, tail intact |
| `code/archive/old-app.backup-2025-01-01` | dots in the directory name | the `~/.claude/projects` encoding is lossy |
| `code/platform` | a head with a child, a grandchild and a great-grandchild (`services/billing/ledger`), plus a `.claude/worktrees/` copy at the bottom | one tree, four levels: the wizard cards, the heads table and the Review list must all nest it; the skip list still holds at the deepest level |
| `code/link-to-webapp`, `code/deep/a/…/project` | a symlink to `code/webapp`; a `CLAUDE.md` nine levels down with no head above it | counted once and never followed; documented as NOT discovered — the head search stops at depth 6, and nothing on that branch made it a tree |
| `code/swift-tool` | `.build/checkouts/dep/CLAUDE.md` | SwiftPM vendored material is skipped |
| `.claude/` | the user's own `settings.json`, six encoded project dirs with transcripts, plugins and junk | `settings.json` must come out byte-identical |

## How to run

```
python3 staging/e2e.py --home /private/tmp/cc-interproject-staging   # --keep to inspect afterwards
python3 -m pytest tests/staging -q
```

`e2e.py` uses `dist/install.py` when `tools/bundle.py --check` calls it current, else a fresh bundle in a temporary directory; it never writes into `dist/`.

## Real-CLI checks (owner-run, or a disposable cloud sandbox)

This costs one sonnet call. Claude Code reads its configuration from `$HOME/.claude`, so the staging
HOME is chosen by setting `HOME`; `claude --help` at v2.1.268 documents no `CLAUDE_CONFIG_DIR`
(grepping its help output for that name returns nothing), so do not rely on it here. Install once
and keep the tree — `e2e.py` uninstalls at step 6, so do not use it for this:

```
python3 staging/build_home.py --out /private/tmp/cc-interproject-manual
printf 'all\ny\n' | PATH="$PWD/fixtures/claude_fake:$PATH" HOME=/private/tmp/cc-interproject-manual python3 dist/install.py --no-browser --root /private/tmp/cc-interproject-manual
```

Law 1 loop. In `.claude/PROJECT_REGISTRY.md` change the `code/webapp` row's `Written by` cell
to `installer`, then run this; it must read `self` afterwards. Remove the tree when done.

```
cd /private/tmp/cc-interproject-manual/code/webapp
HOME=/private/tmp/cc-interproject-manual claude -p "Do what your CLAUDE.md tells you to do on your first session, then reply DONE." --allowedTools Read Edit Write Glob --max-turns 8 --output-format json
grep "code/webapp |" /private/tmp/cc-interproject-manual/.claude/PROJECT_REGISTRY.md
```
