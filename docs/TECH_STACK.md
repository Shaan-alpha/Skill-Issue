# Tech Stack

> Every library, version target, and the reason it is in the stack. Update whenever a dependency is added, removed, or version-pinned for a reason worth remembering.

---

## Frontend — `frontend/`

| Tool | Pinned (as of 2026-05-15) | Why |
| --- | --- | --- |
| **Next.js** | `16.2.6` | App Router, partial prerendering, streaming, Vercel-native. v16 dropped some conventions; check `frontend/AGENTS.md` before assuming v13/v14 patterns. |
| **React** | `19.2.4` | Server Components, Actions, the modern data flow |
| **TypeScript** | `^5` | Sane component contracts |
| **TailwindCSS** | `^4` | Utility-first; `@tailwindcss/postcss` is the v4 pipeline. No tailwind.config — config lives in `globals.css` via `@theme`. |
| **tw-animate-css** | `^1.4` | v4-compatible replacement for `tailwindcss-animate` |
| **shadcn/ui** | `^4.7` (devDependency, CLI only) | Component baseline; we own the source. The package is a CLI scaffolder — *do not* import from it at runtime. Style: `base-nova` (Base UI primitives, not Radix). |
| **Framer Motion** | `^12.38` | Animation; prefer spring physics over linear easings. Use `LazyMotion` + `m.*` namespace, not `motion.*`, to keep the initial bundle lean. |
| **@base-ui/react** | `^1.4` | Headless primitives (Progress, Tooltip) — accessible and unstyled; we own the visual layer. Used for the v0.3.0 position-bar Progress and badge-row Tooltip. |
| **lucide-react** | `^1.16` | Icon set. **Branded icons (`Github`, `Twitter`, etc.) were removed in 1.x** — substitute generic equivalents (`ExternalLink`) or inline an SVG. |
| **Magic UI / Aceternity** | latest, on-demand | Motion accents — used sparingly |
| **@vercel/og** | latest | OG card generation (v0.7.0) |
| **next-themes** | latest | Dark-mode default with light variant |
| **zod** | latest | Runtime schema validation at API boundaries |

**Bundler:** Turbopack (Next.js default in 16+).

**Linting / formatting:** **ESLint** via `eslint-config-next` 16.2.6. Decision logged 2026-05-15 — chosen because the Next.js codemods and recommended rules ship through this config. Revisit Biome at v0.8.0 if perf or DX warrants.

---

## Backend — `backend/`

| Tool | Pinned (as of 2026-05-15) | Why |
| --- | --- | --- |
| **Python** | `3.12+` | Modern type system, performance, structural pattern matching |
| **FastAPI** | `0.136` | Async-native, Pydantic-integrated, OpenAPI for free |
| **Pydantic** | `2.13` | Models for every API boundary and every scorer output |
| **pydantic-settings** | `2.14` | `.env` + env-var loading for `Settings` |
| **httpx** | `0.28` (with `h2`) | Async HTTP client with HTTP/2 multiplexing |
| **uvicorn[standard]** | `0.47` | ASGI server in dev; production server decided in v0.5.0 |
| **uv** | `0.11.12+` | Package + venv management — significantly faster than pip |
| **pytest** | `9.x` | Test runner with async support |
| **pytest-asyncio** | `1.3` | `asyncio_mode = "auto"` so async tests don't need decorators |
| **respx** | `0.23` | httpx mocking for GitHub client + e2e tests |
| **ruff** | `0.15.13` | Linter + formatter — one tool for both. Configured in `backend/ruff.toml` (py312, line 100, E/F/I/UP/B/SIM/TCH/RUF). |
| Static typing | deferred — ruff covers the lint surface | The mypy/pyright pick was punted past v0.1.0; revisit at v0.5.0 when ORM types land |

**Package manager:** `uv` (not pip, not poetry). Faster, simpler, lockfile-first.

---

## Data layer

| Tool | Role |
| --- | --- |
| **Neon Postgres** | Primary store (users, analyses, narratives, share tokens). Branch-per-PR for migrations. |
| **Upstash Redis** | Edge-friendly cache and rate-limit token buckets |
| **Alembic** _or_ **Drizzle** | Migrations — decide in v0.5.0 based on backend host |

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
| **`openai` Python SDK** | OpenAI-compatible client. Used against any provider that ships an OpenAI-compatible chat API, not just OpenAI. |
| **Groq + `llama-3.3-70b-versatile`** | Production default since v0.5.0. Free tier (30 RPM, 14,400 RPD), faster than GPT-4o, ~95% quality on creative writing. Configured via `NARRATIVE_BASE_URL=https://api.groq.com/openai/v1` + `NARRATIVE_MODEL=llama-3.3-70b-versatile`. |
| Provider abstraction | `NarrativeLLM` in [`backend/app/narrative/llm.py`](../backend/app/narrative/llm.py) accepts `base_url`. Pointing at any OpenAI-compatible endpoint (Groq, OpenRouter, Cerebras, vLLM/Ollama, OpenAI itself) requires only env-var changes — no code. |

**Cost guardrails:** per-request `max_tokens` cap, per-day per-instance request budget (`NARRATIVE_DAILY_LIMIT`, default 50). Groq's free tier means out-of-pocket cost stays at $0 for v0.5.0; the in-process budget is conservative defence against runaway loops, not a billing guard.

**Model comparison tool:** [`backend/tools/compare_narratives.py`](../backend/tools/compare_narratives.py) runs ingestion + scoring + both narrative modes against a configurable list of Groq models and dumps the outputs side-by-side. Re-run when picking a new default model.

---

## Deployment

| Surface | Host | Notes |
| --- | --- | --- |
| Frontend | **Vercel** | Native Next.js 16 support, edge OG, runtime cache |
| Backend | **Vercel Functions (Fluid Compute)** | Locked 2026-05-15. Same dashboard as frontend, OIDC env handoff, native marketplace integration with Neon + Upstash. Long re-ingestion runs split via Vercel Cron in v0.8.0 to stay within function duration caps. |
| DB | **Neon** | Vercel Marketplace install when ready |
| Cache | **Upstash Redis** | Vercel Marketplace install when ready |
| DNS / domain | Vercel-managed | Custom domain decided pre-v1.0 |

---

## Observability

| Tool | Role | Slice |
| --- | --- | --- |
| **Sentry** | Error tracking (frontend + backend) | v0.9.0 |
| **PostHog** or **Plausible** | Product analytics — preference: privacy-first, no third-party cookies | v0.9.0 |
| Structured logs | Backend routes emit JSON logs to host's log pipe | v0.9.0 |
| Sentry budget alerts | Cost ceiling on OpenAI | v0.4.0 onward |

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
