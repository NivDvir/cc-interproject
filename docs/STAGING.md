# Staging harness

`staging/` builds a throwaway HOME that looks like a real user's machine and runs the bundled
installer against it with the fake `claude` from `fixtures/claude_fake`; this machine's own
`~/.claude` is never touched. `fixtures/forest` proves single behaviours, this proves they hold
together on a messy one.

## What the cases model

| Case | Models | Why it is here |
|---|---|---|
| `code/webapp` | Node, `.git/`, `node_modules/` holding a CLAUDE.md | the common project, and the common decoy |
| `code/api` | Python, `.venv/.../site-packages/CLAUDE.md`, own CLAUDE.md with no heading | the name falls back to the directory |
| `code/monorepo` | root plus two package CLAUDE.md files, plus `.claude/worktrees/` | subtrees nest under their root; a worktree copy is not a project |
| `Documents/thesis` | 200 lines, headings, tables, code fences | a long file survives the append unchanged |
| `code/ml-lab` | UTF-8 BOM and CRLF | a Windows-authored file must keep its bytes |
| `code/dotfiles` | empty (0 byte) CLAUDE.md | an empty project still earns a registry row |
| `Projects/Client Work/acme site` | spaces in the path, French prose | quoting, and non-ASCII left alone |
| `code/legacy` | an existing kit block with text after it | idempotence: still one block, tail intact |
| `code/archive/old-app.backup-2025-01-01` | dots in the directory name | the `~/.claude/projects` encoding is lossy |
| `code/link-to-webapp`, `code/deep/a/…/project` | a symlink to `code/webapp`; a project nine levels down | counted once and never followed; documented as NOT discovered (depth cap 6) |
| `code/swift-tool` | `.build/checkouts/dep/CLAUDE.md` | SwiftPM vendored material is skipped |
| `.claude/` | foreign PostToolUse and UserPromptSubmit hooks, permissions, model, env, six encoded project dirs with transcripts, plugins and junk | the installer merges, never replaces |

## How to run

```
python3 staging/e2e.py --home /private/tmp/six-laws-staging   # --keep to inspect afterwards
python3 -m pytest tests/staging -q
```

`e2e.py` uses `dist/install.py` when `tools/bundle.py --check` calls it current, else a fresh bundle in a temporary directory; it never writes into `dist/`.

## Real-CLI checks (manual, owner-run)

Both cost one sonnet call. Claude Code reads its configuration from `$HOME/.claude`, so the staging
HOME is chosen by setting `HOME`; `claude --help` at v2.1.268 documents no `CLAUDE_CONFIG_DIR`
(grepping its help output for that name returns nothing), so do not rely on it here. Install once
and keep the tree — `e2e.py` uninstalls at step 6, so do not use it for this:

```
python3 staging/build_home.py --out /private/tmp/six-laws-manual
printf 'all\ny\ny\n' | PATH="$PWD/fixtures/claude_fake:$PATH" HOME=/private/tmp/six-laws-manual python3 dist/install.py --no-browser --root /private/tmp/six-laws-manual
```

(a) Hook firing. The three hooks must run and leave their state:

```
cd /private/tmp/six-laws-manual/code/webapp
HOME=/private/tmp/six-laws-manual claude -p "Reply with the single word OK." --max-turns 1 --output-format json
ls /private/tmp/six-laws-manual/.claude/six-laws-state/turn-loads.*
grep -l "Plan the task first" "$(ls -t /private/tmp/six-laws-manual/.claude/projects/*/*.jsonl | head -1)"
```

(b) Law 1 loop. In `.claude/PROJECT_REGISTRY.md` change the `code/webapp` row's `Written by` cell
to `installer`, then run this; it must read `self` afterwards. Remove the tree when done.

```
cd /private/tmp/six-laws-manual/code/webapp
HOME=/private/tmp/six-laws-manual claude -p "Do what your CLAUDE.md tells you to do on your first session, then reply DONE." --allowedTools Read Edit Write Glob --max-turns 8 --output-format json
grep "code/webapp |" /private/tmp/six-laws-manual/.claude/PROJECT_REGISTRY.md
```
