# Design System UI

The React component package. Every component is a named export from `src/index.ts`.

Components take a `className` and forward refs. No component fetches data or reads
global state. Styling comes from the tokens in the `core` package, never from a
hard-coded colour.

Storybook runs with `pnpm dev` and is the fastest way to see a change.
