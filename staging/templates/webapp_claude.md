# Storefront Web App

The customer-facing storefront. React 18, Vite, TypeScript. It talks to the API service
in `code/api` over REST and to Stripe for payment intents.

## Layout

- `src/routes/` one file per page, lazy loaded.
- `src/components/` shared presentational components, no data fetching.
- `src/lib/api.ts` the only place that knows the API base URL.
- `tests/` Vitest unit tests; Playwright end-to-end tests live in `e2e/`.

## Commands

- `npm run dev` starts Vite on port 5173.
- `npm test` runs Vitest once.
- `npm run e2e` needs the API running locally first.
- `npm run build` must stay under a 400 kB gzipped main chunk.

## Conventions

- No default exports.
- Data fetching happens in route loaders, never inside a component body.
- Every form control needs a label; the accessibility tests fail otherwise.
- Feature flags come from `src/lib/flags.ts` and default to off.

## Gotchas

The Vite dev server proxies `/api` to port 8000. If requests 404 in development but
work in production, the proxy is the first thing to check.

Images are served from a CDN in production and from `public/` in development, so a
missing image will not show up until a preview deploy.

## Release

Merging to `main` publishes a preview. A tagged release promotes the preview to
production. Do not tag without a green end-to-end run.

Rollback is a redeploy of the previous tag; there is no separate rollback command.
