# Design System Core

Design tokens, colour maths, and framework-free helpers. No React, no DOM.

The token source of truth is `tokens.json`; the TypeScript and CSS outputs are both
generated from it by `pnpm build:tokens`. Edit the JSON, never the generated files.

Contrast checks run in CI: a token pair below 4.5:1 fails the build.
