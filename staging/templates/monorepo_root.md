# Design System Monorepo

The shared design system. pnpm workspaces, Turborepo, changesets for versioning.

Two published packages live under `packages/`: `ui` (React components) and `core`
(tokens and framework-free helpers). Anything else under `packages/` is private.

## Rules

- `core` must never import from `ui`.
- A change to a public export needs a changeset in the same pull request.
- `pnpm -w build` builds every package in dependency order.
- Visual regression snapshots live in `packages/ui/__snapshots__/`.
