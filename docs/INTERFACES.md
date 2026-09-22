# Interfaces (v1) — every cross-module signature. Workers build against THIS, not each other's code.

All modules: `from __future__ import annotations`. Types below use Python 3.9 syntax.

## run_state.py
```python
@dataclass
class Tree:
    path: Path; name: str; claude_md: Path
    has_session: bool = False; last_session: Optional[str] = None   # ISO date or None
    subtrees: List["Tree"] = field(default_factory=list); selected: bool = False

@dataclass
class Row:
    name: str; owns: str; asks_others_to_watch_for: str; contact_subject: str
    written_by: str            # "self" | "installer"
    status: str                # "ok" | "fallback" | "timeout" | "error" | "authfail"
    seconds: float = 0.0

@dataclass
class Action:
    kind: str                  # "create_file" | "append_line" | "insert_block"
    target: Path; marker_id: Optional[str]; payload: str
    existing_text: Optional[str]; diff: str; existed: bool

@dataclass
class Run:
    mode: str                  # "install" | "dry-run" | "uninstall" | "status"
    home: Path; claude_dir: Path; root: Path            # root = scan root (== home unless --root)
    no_browser: bool; claude_bin: Optional[str] = None
    claude_caps: Dict[str, bool] = field(default_factory=dict)   # {"json_schema": bool}
    auth_ok: bool = False
    trees: List[Tree] = field(default_factory=list)
    rows: Dict[str, Row] = field(default_factory=dict)            # key = str(tree.path)
    ask_progress: Dict[str, str] = field(default_factory=dict)    # waiting|asked|answered|fallback|timeout
    scan_progress: Dict[str, object] = field(default_factory=dict)  # {"done": bool, "dirs_seen": int, "skipped_roots": [...]}
    plan: List[Action] = field(default_factory=list)
    install_progress: Dict[str, object] = field(default_factory=dict)  # {"done","current","completed","total","errors"}
    errors: List[str] = field(default_factory=list)
    step: str = "welcome"; token: str = ""; confirmed: bool = False
    lock: threading.Lock = field(default_factory=threading.Lock)

def new_run(args: argparse.Namespace) -> Run
def selected_trees(run: Run) -> List[Tree]          # flattened, selected only, tree order
```

## paths.py
```python
KIT_NAME = "cc-interproject"; MANIFEST_NAME = "interproject.manifest.json"; BACKUPS_SUBDIR = "interproject-backups"
def skip_names() -> Set[str]                         # per-OS directory names never entered
def home_dir() -> Path                               # $HOME override else Path.home() (Windows ignores HOME)
def is_windows_shim(claude_bin: str) -> bool          # True if claude_bin resolves to a .cmd/.bat file
def windows_shim_argv(command: List[str]) -> List[str]  # wraps command in cmd.exe /d /c when shimmed
def manifest_path(claude_dir: Path) -> Path
def backups_dir(claude_dir: Path, stamp: str) -> Path
def encode_project_dir(path: Path) -> List[str]      # candidate ~/.claude/projects names, forward-encoded
```

## discover/
```python
walk.find_projects(root: Path, skip: Set[str], on_progress: Callable[[int], None], max_depth: int = 6,
                   max_dirs: int = 200_000) -> Tuple[List[Path], List[Path]]   # (claude_md paths, skipped roots)
# max_depth bounds the search for HEADS only; inside a tree already found the walk is unbounded.
forest.build(claude_mds: List[Path]) -> List[Tree]   # top-level trees with nested subtrees
forest.apply_selection(trees: List[Tree], selected: Set[str]) -> int   # str paths; subtrees inherit; returns count
sessions.annotate(trees: List[Tree], claude_dir: Path) -> None     # sets has_session/last_session
```

## heads/
```python
preflight.find_claude(run: Run) -> Optional[str]          # sets run.claude_bin
preflight.probe_capabilities(run: Run) -> Dict[str, bool] # sets run.claude_caps
preflight.auth_ping(run: Run, timeout: int = 60) -> bool  # sets run.auth_ok
packet.PACKET: str; packet.ROW_SCHEMA: dict
packet.build_command(claude_bin: str, json_schema: bool) -> List[str]
ask.start(run: Run, max_workers: int = 4, timeout: int = 120) -> None   # background; fills rows + ask_progress
ask.ask_one(claude_bin: str, tree: Tree, json_schema: bool, timeout: int) -> Row  # blocking, used by start
ask.parse_row(envelope_text: str) -> Optional[Dict[str, str]]
ask.is_auth_failure_text(text: str) -> bool
ask.all_done(run: Run) -> bool
fallback.row_from_claude_md(claude_md: Path, seconds: float, status: str) -> Row
```

## write/
```python
blocks.BEGIN = "<!-- cc-interproject:begin id={id} v={v} -->"; blocks.END = "<!-- cc-interproject:end id={id} -->"
blocks.render(marker_id: str, version: int, body: str) -> str
blocks.contains(text: str, marker_id: str) -> bool
blocks.insert(text: str, block: str) -> Tuple[str, bool, bool]     # (new_text, leading_blank_added, trailing_newline_added)
blocks.strip(text: str, marker_id: str) -> Tuple[str, bool]         # (new_text, found_exactly_once)
registry.render(rows: Dict[str, Row], trees: List[Tree], header: str) -> str
plan.build(run: Run) -> List[Action]                # pure; reads disk, writes nothing; sets run.plan
plan.render_text(actions: List[Action]) -> str      # for --dry-run and the terminal UI
apply.execute(run: Run, on_progress: Callable[[str, int, int], None]) -> Path   # returns manifest path
```

## manifest/
```python
record.new(run: Run, stamp: str) -> dict
record.add_entry(manifest: dict, entry: dict) -> None
record.write(manifest: dict, path: Path) -> None
record.load(path: Path) -> Optional[dict]
record.sha256(path: Path) -> str
uninstall.run(run: Run, restore_backups: bool = False, ask: Callable[[str], bool] = ...) -> int   # exit code
status.run(run: Run) -> int
status.report(manifest: dict, claude_dir: Path) -> str
```

## texts/
```python
loader.read(name: str) -> str          # "INTERPROJECT_LAWS.md" etc.; works from source tree and from the zipapp
loader.names() -> List[str]
```

## wizard/
```python
launch.open_ui(run: Run) -> int        # starts server, opens browser, blocks until quit; returns exit code
launch.can_open_browser() -> bool
server.make_server(run: Run) -> ThreadingHTTPServer     # bound 127.0.0.1:0
server.render_page(token: str) -> str   # inlines wizard.css, wizard.js, wizard2.js, icons.svg
api.state(run) -> dict; api.scan_start(run) -> dict; api.scan_progress(run) -> dict
api.set_selection(run, selected: List[str]) -> dict
api.heads_start(run) -> dict; api.heads_progress(run) -> dict
api.plan(run) -> dict; api.install_start(run, confirm: bool) -> dict; api.install_progress(run) -> dict
api.done(run) -> dict; api.quit(run) -> dict
terminal.run(run: Run) -> int          # same steps, numbered prompts on stdin
```
HTTP table (all `/api/*` require header `X-Kit-Token`; JSON in/out; 403 on bad token/Origin/Host):
GET `/?t=` page · GET `/api/state` · POST `/api/scan` → 202 · GET `/api/scan` · POST `/api/selection`
{selected:[paths]} · POST `/api/heads` → 202 · GET `/api/heads`
{done, results:[{path,status,seconds,row?}]} · GET `/api/plan` {actions:[{kind,target,existed,diff,bytes}],
warnings:[]} · POST `/api/install` {confirm:true} → 202 (409 if not confirmed or dry-run) ·
GET `/api/install` · GET `/api/done` {paste_block, manifest_path, uninstall_cmd, self_rows, installer_rows}
· POST `/api/quit`. The page JS reads the token from `window.KIT_TOKEN`.

## cli.py
Exit codes: 0 ok · 2 bad arguments · 3 claude not found · 4 not logged in · 5 install error · 6 user aborted.
Flags: `--dry-run` `--uninstall` `--restore-backups` `--status` `--no-browser` `--root <dir>` `--version`.

## Amendments (2026-09-22, from packet C — binding on the server)
- `GET /api/state` returns `{step, mode, dry_run, home, claude_version, trees}` where `trees` is the
  nested Tree list (path, name, has_session, last_session, subtrees, selected) once a scan has run
  (else `[]`).
- `POST /api/quit` must accept the token EITHER in the `X-Kit-Token` header OR as `{"token": ...}` in
  the JSON body, because `navigator.sendBeacon` cannot set headers.
- `POST /api/selection` receives only checked TOP-LEVEL tree paths; the server applies inheritance.
