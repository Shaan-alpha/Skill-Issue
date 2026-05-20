# skill-issue-frontend

Next.js 16 frontend for **Skill Issue** — landing page, analyze flow, results view, share view, and shareable OG cards.

See the repo root [`README.md`](../README.md), [`PLAN.md`](../PLAN.md), [`ARCHITECTURE.md`](../ARCHITECTURE.md), and [`AGENTS.md`](../AGENTS.md) for context. Frontend-specific Next.js warnings live in [`AGENTS.md`](./AGENTS.md) (this directory).

## Local development

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

The backend must also be running for `/u/[username]` to do anything useful. See the root [`README.md`](../README.md) for the two-terminal setup.

### Environment

`frontend/.env.local`:

```bash
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000     # optional — drives the absolute Copy-URL value on /u/[username]/card
```

`NEXT_PUBLIC_BACKEND_URL` defaults to `http://localhost:8000` if unset. `NEXT_PUBLIC_SITE_URL` falls back to the production host.

## Build + lint + test

```bash
npm run lint
npm run test:run
npm run build
```

- **`npm run lint`** — ESLint via `eslint-config-next`.
- **`npm run test:run`** — Vitest 3 + happy-dom + Testing Library (added in v0.6.0). 22 unit + snapshot tests cover the OG palette, data fetchers, OgCard, and CardActions.
- **`npm run build`** — TypeScript + Next 16 build with Turbopack.

## Stack

See [`docs/TECH_STACK.md`](../docs/TECH_STACK.md) for the canonical version pins. Quick reference:

- Next.js 16 (Turbopack), React 19, TypeScript 5
- Tailwind 4 (config in `src/app/globals.css` via `@theme`, no `tailwind.config.*`)
- shadcn/ui (style: `base-nova` — Base UI primitives; CLI-only dependency)
- framer-motion for animation, lucide-react for icons
- `next/og` `ImageResponse` for OG card generation (v0.6.0), Inter Medium + Bold bundled under `public/fonts/` (OFL 1.1)
- Vitest + happy-dom + Testing Library for unit tests (v0.6.0)

## Routes

| Route | Type | Purpose |
| --- | --- | --- |
| `/` | Static | Landing page with search bar |
| `/u/[username]` | Dynamic (SSR) | Results page; fetches `GET /analyze/{username}` from the backend |
| `/u/[username]/card` | Dynamic (SSR) | Card preview page with Copy PNG / Download PNG / Copy URL (v0.6.0) |
| `/u/[username]/opengraph-image` | Dynamic | 1200×630 PNG via `next/og`; auto-wires `<meta property="og:image">` (v0.6.0) |
| `/u/[username]/twitter-image` | Dynamic | Same PNG, auto-wires `<meta name="twitter:image">` (v0.6.0) |
| `/share/[slug]` | Dynamic (SSR) | Public read-only view of a shared analysis (v0.5.0) |
| `/share/[slug]/opengraph-image` / `twitter-image` | Dynamic | OG/Twitter cards for shared analyses (v0.6.0) |
| `/me` | Dynamic (SSR) | Authenticated history grid (v0.5.0) |
| `/_not-found` | Static | Next.js default global 404 |

Segment-level `loading.tsx`, `error.tsx`, and `not-found.tsx` live under `app/u/[username]/`.
