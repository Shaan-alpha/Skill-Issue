# Tech Stack

> Every library, version target, and the reason it is in the stack. Update whenever a dependency is added, removed, or version-pinned for a reason worth remembering.

---

## Frontend — `frontend/`

| Tool | Target version | Why |
| --- | --- | --- |
| **Next.js** | 15.x | App Router, partial prerendering, streaming, Vercel-native |
| **React** | 19.x | Server Components, Actions, the modern data flow |
| **TypeScript** | 5.x | Required for sane component contracts |
| **TailwindCSS** | 4.x where stable, otherwise 3.4 | Utility-first; matches the design philosophy |
| **shadcn/ui** | latest CLI | Component baseline; we own the source, not a node_module |
| **Framer Motion** | latest | Physics-based animation, layout transitions |
| **Magic UI / Aceternity** | latest | Motion accents, hero patterns — used sparingly |
| **lucide-react** | latest | Icon set — clean, consistent line weight |
| **@vercel/og** | latest | OG card generation (v0.6.0) |
| **next-themes** | latest | Dark-mode default with light variant |
| **zod** | latest | Runtime schema validation at API boundaries |

**Bundler:** Turbopack (Next.js default in 15+).

**Linting / formatting:** Biome or ESLint+Prettier — pick one in v0.2.0 and log the decision. Default to **Biome** unless it lacks a critical rule.

---

## Backend — `backend/`

| Tool | Target version | Why |
| --- | --- | --- |
| **Python** | 3.12+ | Modern type system, performance, structural pattern matching |
| **FastAPI** | latest | Async-native, Pydantic-integrated, OpenAPI for free |
| **Pydantic** | 2.x | Models for every API boundary and every scorer output |
| **httpx** | latest | Async HTTP client with HTTP/2 |
| **uvicorn** | latest | ASGI server in dev; production server decided in v0.4.0 |
| **uv** | latest | Package + venv management — significantly faster than pip |
| **pytest** | latest | Test runner with async support |
| **pytest-asyncio** | latest | Async test fixtures |
| **respx** | latest | httpx mocking for GitHub client tests |
| **ruff** | latest | Linter + formatter — one tool for both |
| **mypy** or **pyright** | latest | Static typing; pick in v0.1.0 |

**Package manager:** `uv` (not pip, not poetry). Faster, simpler, lockfile-first.

---

## Data layer

| Tool | Role |
| --- | --- |
| **Neon Postgres** | Primary store (users, analyses, narratives, share tokens). Branch-per-PR for migrations. |
| **Upstash Redis** | Edge-friendly cache and rate-limit token buckets |
| **Alembic** _or_ **Drizzle** | Migrations — decide in v0.4.0 based on backend host |

---

## Auth

| Tool | Role |
| --- | --- |
| **GitHub OAuth** | Sign-in + higher API rate limits. Scopes: `read:user`, `public_repo`. Never `repo` or `admin:*`. |
| **JOSE / authlib** | JWT signing for short-lived session cookies |

---

## AI

| Tool | Role |
| --- | --- |
| **OpenAI SDK** | Default narrative provider. Latest GPT class for long narratives, cheap small model for short summaries. |
| Provider abstraction | All OpenAI calls go through `narrative/llm.py` so swapping providers (Anthropic, local) is a one-file change |

**Cost guardrails:** per-request budget, per-day project budget, alerting via Sentry.

---

## Deployment

| Surface | Host | Notes |
| --- | --- | --- |
| Frontend | **Vercel** | Native Next.js 15 support, edge OG, runtime cache |
| Backend | **Vercel Functions (Fluid Compute)** | Locked 2026-05-15. Same dashboard as frontend, OIDC env handoff, native marketplace integration with Neon + Upstash. Long re-ingestion runs split via Vercel Cron in v0.7.0 to stay within function duration caps. |
| DB | **Neon** | Vercel Marketplace install when ready |
| Cache | **Upstash Redis** | Vercel Marketplace install when ready |
| DNS / domain | Vercel-managed | Custom domain decided pre-v1.0 |

---

## Observability

| Tool | Role | Slice |
| --- | --- | --- |
| **Sentry** | Error tracking (frontend + backend) | v0.8.0 |
| **PostHog** or **Plausible** | Product analytics — preference: privacy-first, no third-party cookies | v0.8.0 |
| Structured logs | Backend routes emit JSON logs to host's log pipe | v0.8.0 |
| Sentry budget alerts | Cost ceiling on OpenAI | v0.3.0 onward |

---

## Development tooling (MCP + plugins)

See [`ARCHITECTURE.md`](../ARCHITECTURE.md#mcp-and-plugin-ecosystem-development-tooling) for the full table. None of these ship to users.

Key ones:
- **GitHub MCP** — repo / PR / issue inspection during dev
- **Context7** — live framework docs (Next.js, React, FastAPI, shadcn)
- **Playwright MCP** — visual verification
- **Postgres MCP** — schema + query introspection
- **Vercel plugin (`vercel:*` skills)** — deploys, env, marketplace, OG, runtime cache
- **shadcn skill** — component installs

---

## Version pinning policy

- **Frameworks** (Next.js, React, FastAPI, Pydantic) — track the latest stable major. Upgrade promptly; log the bump.
- **Libraries** — caret-range (`^x.y.z`) by default; pin exact only when a regression forces it. Document the pin in this file.
- **Security patches** — applied within 48 hours of disclosure.

---

## Banned / discouraged

- ❌ jQuery, Lodash for things modern JS does natively
- ❌ Moment.js (use `date-fns` or `Temporal` when stable)
- ❌ CSS-in-JS libraries that add runtime cost (Emotion, styled-components) — Tailwind covers our needs
- ❌ Redux for app state — Server Components + URL state + small client stores suffice
- ❌ Material UI / Chakra — design language conflicts with the Apple/Linear-tier aesthetic
- ❌ Vague ML libraries that promise "AI insights" — we own the analysis
