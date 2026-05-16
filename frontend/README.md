# skill-issue-frontend

Next.js 16 frontend for **Skill Issue** — landing page, analyze flow, and the results view that consumes the FastAPI backend.

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
```

This is the only frontend env var as of v0.2.0. Defaults to `http://localhost:8000` if unset.

## Build + lint

```bash
npm run lint
npm run build
```

The build runs TypeScript and generates static pages for `/` and `/_not-found`. `/u/[username]` is a dynamic server-rendered route.

## Stack

See [`docs/TECH_STACK.md`](../docs/TECH_STACK.md) for the canonical version pins. Quick reference:

- Next.js 16 (Turbopack), React 19, TypeScript 5
- Tailwind 4 (config in `src/app/globals.css` via `@theme`, no `tailwind.config.*`)
- shadcn/ui (style: `base-nova` — Base UI primitives; CLI-only dependency)
- framer-motion for animation, lucide-react for icons

## Routes

| Route | Type | Purpose |
| --- | --- | --- |
| `/` | Static | Landing page with search bar |
| `/u/[username]` | Dynamic (SSR) | Results page; fetches `GET /analyze/{username}` from the backend |
| `/_not-found` | Static | Next.js default global 404 |

Segment-level `loading.tsx`, `error.tsx`, and `not-found.tsx` live under `app/u/[username]/`.
