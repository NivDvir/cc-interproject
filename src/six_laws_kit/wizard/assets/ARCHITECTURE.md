# wizard/assets — architecture

`server.render_page(token)` reads `index.html` once per request and does four textual
substitutions, nothing else: `<!--@css-->` is replaced by the contents of `wizard.css`,
`<!--@js-->` by `wizard.js`, `<!--@js2-->` by `wizard2.js`, and `<!--@icons-->` (placed right
after `<body>`) by `icons.svg`. The result is one self-contained HTML response with no follow-up
asset requests, so the wizard works offline. `%%TOKEN%%` in the inline `<script>` is replaced by
the per-run token; the page then sends that token back as header `X-Kit-Token` on every `/api/*`
call, and (since `navigator.sendBeacon` cannot set headers) as a JSON body field on the
`pagehide` beacon to `/api/quit`.

## Why the JS is two files

`STYLE.md` caps a file at 400 lines. `wizard.js` is the controller — the step machine, the HTTP
client, and the six step transitions — and `wizard2.js` holds every DOM builder. They are two
separate inline `<script>` blocks in that order, so both are plain top-level scripts sharing one
global scope: `wizard2.js` reads `state` and `headsStart` from `wizard.js`, and `wizard.js` calls
`renderForest`, `renderSkipped`, `renderHeadsRows`, `headsRow`, `renderReview` and `cssEscape`
from `wizard2.js`. Order is safe because nothing in `wizard2.js` runs at load time and every call
into it happens inside an event or poll callback, long after both blocks have been evaluated.
`tests/wizard/test_server.py` asserts every include mark is substituted and that the controller
comes first.

## The forest, as the page shows it

The Scan step renders each top-level tree as a `<fieldset class="tree-card">` whose `<legend>` is
the head's name: the head's own row carries the checkbox (labelled with that name), the path, the
last session and a subtree-count tag, and the whole subtree hierarchy hangs beneath it as nested
`<ul class="subtrees">` lists with `aria-level` per item and connector elbows drawn with CSS
borders (no images). Depth is unbounded — grandchildren and deeper render the same way.
Selecting a head selects the whole tree, so subtrees carry no checkbox of their own and are shown
as `inherited`, greyed until the head is checked. The Register-heads table and the Review list
group their rows by tree in that same order, with the same 20px indentation step.

Contract with the server: these six files are the entire page. No build step, no bundler, no
external network resource (fonts, CDNs) — system font stack only. `wizard.js` talks to the HTTP
API exactly as listed in `docs/INTERFACES.md`; it never assumes a field the server does not
document. One field is inferred rather than stated verbatim in `INTERFACES.md` and is called out
here: `GET /api/state` is assumed to carry `dry_run` alongside `trees` (nested `Tree` records),
since the Scan step needs that data from somewhere and no other endpoint carries it.

Per **STYLE.md**, none of this is ever embedded as a Python string; `write/` and `wizard/server.py`
only read these files from disk.

Contrast ratios chosen (WCAG AA, text needs 4.5:1, all pairs measured well above it):
light ink/bg 16.3:1, ink-soft/bg 5.7:1, accent/bg 6.9:1, good/good-soft 7.0:1, warn/warn-soft
6.5:1, bad/bad-soft 6.5:1; dark ink/bg 15.3:1, ink-soft/bg 7.0:1, accent/bg 9.0:1, good/good-soft
7.0:1, warn/warn-soft 7.0:1, bad/bad-soft 6.2:1.
