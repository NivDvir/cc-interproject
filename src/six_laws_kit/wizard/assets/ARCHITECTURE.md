# wizard/assets — architecture

`server.render_page(token)` reads `index.html` once per request and does three textual
substitutions, nothing else: `<!--@css-->` is replaced by the contents of `wizard.css`,
`<!--@js-->` by `wizard.js`, and `<!--@icons-->` (placed right after `<body>`) by `icons.svg`.
The result is one self-contained HTML response with no follow-up asset requests, so the wizard
works offline. `%%TOKEN%%` in the inline `<script>` is replaced by the per-run token; the page
then sends that token back as header `X-Kit-Token` on every `/api/*` call, and (since
`navigator.sendBeacon` cannot set headers) as a JSON body field on the `pagehide` beacon to
`/api/quit`.

Contract with the server: these five files are the entire page. No build step, no bundler, no
external network resource (fonts, CDNs) — system font stack only. `wizard.js` talks to the HTTP
API exactly as listed in `docs/INTERFACES.md`; it never assumes a field the server does not
document. Two fields are inferred rather than stated verbatim in `INTERFACES.md` and are called
out here: `GET /api/state` is assumed to carry `dry_run`, `trees` (nested `Tree` records) and
`same_purpose_hooks`, since Modules and Scan need that data from somewhere and no other endpoint
carries it.

Per **STYLE.md**, none of this is ever embedded as a Python string; `write/` and `wizard/server.py`
only read these files from disk.

Contrast ratios chosen (WCAG AA, text needs 4.5:1, all pairs measured well above it):
light ink/bg 16.3:1, ink-soft/bg 5.7:1, accent/bg 6.9:1, good/good-soft 7.0:1, warn/warn-soft
6.5:1, bad/bad-soft 6.5:1; dark ink/bg 15.3:1, ink-soft/bg 7.0:1, accent/bg 9.0:1, good/good-soft
7.0:1, warn/warn-soft 7.0:1, bad/bad-soft 6.2:1.
