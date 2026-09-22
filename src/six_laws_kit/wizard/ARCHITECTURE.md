# wizard/ — architecture

Full design: `../../../docs/DESIGN.md` (§2 data flow, §3 wizard/Python contract).
Signatures and the HTTP table: `../../../docs/INTERFACES.md`, including its Amendments.
This file is a map, not a duplicate of either.

## Files

| File | Job |
|---|---|
| `api.py` | The twelve actions behind the endpoints. Each takes the `Run`, mutates it under `run.lock`, and returns a plain dict. The two long steps (`scan_start`, `install_start`) run on daemon threads and report through a lock-guarded progress dict the page polls. This is the one module here allowed to call across categories. |
| `server.py` | `ThreadingHTTPServer` on `127.0.0.1:0`, the token / Host / Origin gates, the `(method, path)` dispatch table, and `render_page`, which inlines the four `assets/` files into one response. |
| `launch.py` | Decides whether a browser can be opened at all, prints the URL, opens it, and blocks in `serve_forever`. |
| `terminal.py` | The same seven steps as numbered stdin prompts, for `--no-browser` and for machines with no display. |
| `assets/` | The real HTML, CSS, JS and SVG files; see `assets/ARCHITECTURE.md`. Never embedded as Python strings. |

## Request handling

Every request passes three gates in order, each a small method on the handler: the `Host` header
must be loopback and any `Origin` header must be this server's own origin (else 403); `GET /`
needs the token in `?t=`, and every `/api/*` call needs it in `X-Kit-Token` (else 403);
`POST /api/quit` also accepts `{"token": ...}` in the body, because `navigator.sendBeacon` cannot
set a header. An unknown path is 404. The three start endpoints answer 202;
`POST /api/install` answers 409 when `api.install_start` returns an `error` — that is, when the
page did not confirm or the run is a dry run. Nothing is ever printed to stdout: `log_message` is
overridden to stay silent unless `KIT_DEBUG` is set, and then it writes to stderr.

## Shutdown

`POST /api/quit` sets `api.QUIT_REQUESTED`, answers 200, then schedules
`threading.Timer(0.3, httpd.shutdown)`. A watchdog thread shuts the server down after 15 minutes
with no request. `launch.open_ui` returns 0 when the server stops, 6 on Ctrl-C, and **7 when no
browser could be opened** — the signal `cli.main` uses to fall back to `terminal.run`. The URL is
printed to stderr before any of that, so it can always be opened by hand.

## Two notes on the data

`scan_progress["dirs_seen"]` is whatever `discover.walk` last reported, and it reports every 200
directories; on a small tree it can stay 0 until the scan is done. `state()["claude_version"]` is
`claude --version`, probed once per binary and cached in this module; it is an empty string when
no CLI was located.

## Import rule

`api.py` may import every category — it and `cli.py` are the orchestrators (`STYLE.md`).
`server.py`, `launch.py` and `terminal.py` may import only the stdlib, `run_state`, `paths`, and
their own siblings here.
