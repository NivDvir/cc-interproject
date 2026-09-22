# tools/

`bundle.py` packs `src/six_laws_kit/` into the single-file installer the README tells readers
to download: a zipapp named `install.py`, plus a `SHA256SUMS` file next to it in `dist/`.

It has two modes: build (the default) writes `dist/install.py` and `dist/SHA256SUMS`; `--check`
rebuilds into a temp directory and fails if the result differs from what is committed, so CI
catches a stale bundle.

`bundle.py` is a build tool, not part of the installed product. It never runs on the end
user's machine and it imports nothing from `six_laws_kit` at runtime — only at build time, to
read the source tree.
