# Tech Stack

> Every library, version target, and the reason it is in the stack. Update whenever a dependency is added, removed, or version-pinned for a reason worth remembering.

---

## Frontend — `frontend/`

| Tool | Pinned (as of 2026-07-13) | Why |
| --- | --- | --- |
| **Next.js** | `16.2.10` | App Router, partial prerendering, streaming, Vercel-native. v16 dropped some conventions; check `frontend/AGENTS.md` before assuming v13/v14 patterns. |
| **Cache Components** | enabled v0.8.6 (`cacheComponents: true` in `next.config.ts`) | Powers `/share/[slug]` PPR via `'use cache'` + `cacheTag('share:<slug>')` + `cacheLife({ revalidate: 3600 })`. Incompatible with `export const dynamic = "force-dynamic"` (had to be dropped from `/me` and `/u/[username]/card`). Helpers from `next/cache`: `cacheTag`, `cacheLife`, `revalidateTag(tag, { expire: 0 })`. Stubbed in vitest setup since they throw outside the Next runtime. |
| **React** | `19.2.7` | Server Components, Actions, the modern data flow |
| **TypeScript** | `^5` | Sane component contracts |
| **TailwindCSS** | `^4` | Utility-first; `@tailwindcss/postcss` is the v4 pipeline. No tailwind.config — config lives in `globals.css` via `@theme`. |
| **tw-animate-css** | `^1.4` | v4-compatible replacement for `tailwindcss-animate` |
| **shadcn/ui** | `^4.13` (devDependency, CLI only) | Component baseline; we own the source. The package is a CLI scaffolder — *do not* import from it at runtime. Style: `base-nova` (Base UI primitives, not Radix). |
| **Framer Motion** | `^12.42` | Animation; prefer spring physics over linear easings. Use `LazyMotion` + `m.*` namespace, not `motion.*`, to keep the initial bundle lean. |
| **@base-ui/react** | `^1.6` | Headless primitives (Progress, Tooltip) — accessible and unstyled; we own the visual layer. Used for the v0.3.0 position-bar Progress and badge-row Tooltip. |
| **lucide-react** | `^1.24` | Icon set. **Branded icons (`Github`, `Twitter`, etc.) were removed in 1.x** — substitute generic equivalents (`ExternalLink`) or inline an SVG. |
| **`next/og` (`ImageResponse`)** | bundled with Next 16 | OG card generation (v0.6.0). File-convention routes `opengraph-image.tsx` + `twitter-image.tsx` at the route segment auto-wire meta tags. Satori-based — strict about explicit `display: flex` on every multi-child div. |
| **Inter font** | OFL 1.1, bundled under `public/fonts/` | Medium + Bold TTF bundled because satori reads font bytes per request — fetching remotely would add cold-start latency. |
| **Vitest** | `^4.1` + `happy-dom@^20` + `@testing-library/react@^16` + `@testing-library/jest-dom@^6` | First frontend test framework, added in v0.6.0. Picked over node:test for native TS/JSX, picked happy-dom over jsdom for speed. happy-dom bumped from `^15` to `^20` on 2026-05-22 to clear GHSA-37j7-fg3j-429f (VM Context Escape RCE — dev-only impact, but AGENTS.md rule 1). |

**Bundler:** Turbopack (Next.js default in 16+).

**Linting / formatting:** **ESLint** via `eslint-config-next` 16.2.10. Decision logged 2026-05-15 — chosen because the Next.js codemods and recommended rules ship through this config. Decision kept through v0.8.0; revisit Biome at v0.9.0 or v1.0 if perf/DX warrants.

---

## Backend — `backend/`

| Tool | Pinned (as of 2026-07-13) | Why |
| --- | --- | --- |
| **Python** | `3.12+` | Modern type system, performance, structural pattern matching |
| **FastAPI** | `0.139` | Async-native, Pydantic-integrated, OpenAPI for free. Bumped 0.136→0.139 in the v1.0.x security slice to pull patched Starlette. |
| **Starlette** | `1.3.1+` | ASGI toolkit under FastAPI; imported directly in `main.py`. Pinned at the CVE-patched floor (PYSEC-2026-248/249, CVE-2026-48817/48818). |
| **Pydantic** | `2.13` | Models for every API boundary and every scorer output |
| **pydantic-settings** | `2.14` | `.env` + env-var loading for `Settings` |
| **httpx** | `0.28` (with `h2`) | Async HTTP client with HTTP/2 multiplexing |
| **SQLAlchemy** | `2.0.x` (async) + `asyncpg>=0.31` | Async ORM + Postgres driver for Neon. Statement cache disabled for pgBouncer transaction-mode pooling. |
| **Alembic** | `1.18+` | Hand-authored migrations; reversibility tested in pytest. |
| **upstash-redis** | `>=1.2` | Async REST-API client for Upstash. HTTP-based, Fluid-Compute-friendly. Added in v0.7.0. |
| **cryptography** | `48.0.1+` | AES-GCM for at-rest GitHub-token encryption (v0.5.0). CVE floor raised (GHSA-537c-gmf6-5ccf) in the v1.0.x security slice. |
| **uvicorn[standard]** | `0.47` | ASGI server in dev; Vercel Functions for production |
| **uv** | `0.11.12+` | Package + venv management — significantly faster than pip |
| **pytest** | `9.x` | Test runner with async support |
| **pytest-asyncio** | `1.3` | `asyncio_mode = "auto"` so async tests don't need decorators |
| **respx** | `0.23` | httpx mocking for GitHub client + e2e tests |
| **ruff** | `0.15.14` | Linter + formatter — one tool for both. Configured in `backend/ruff.toml` (py312, line 100, E/F/I/UP/B/SIM/TCH/RUF). Note: `ruff check` and `ruff format` are independent passes — run both, not just one. v0.8.0 post-ship audit caught 51 format-drifted files because only `ruff check` was being enforced. |
| Static typing | deferred — ruff covers the lint surface | The mypy/pyright pick was punted past v0.1.0; revisit when payoff justifies the maintenance |

**Package manager:** `uv` (not pip, not poetry). Faster, simpler, lockfile-first.

---

## Data layer

| Tool | Role |
| --- | --- |
| **Neon Postgres** | Primary store (users, analyses, narratives, share tokens). Branch-per-PR for migrations. Pooled host (port 6543, `statement_cache_size=0`) at runtime; direct host (5432) for Alembic. |
| **Upstash Redis** | Backend cache across four fail-open layers (full Report, GitHub API responses, narrative + daily budget, singleflight locks). REST API via `upstash-redis`. User-provisioned account, env vars pasted into Vercel manually. |
| **Alembic** | Migrations — chosen v0.5.0. Hand-authored, reversibility tested. |

---

## Auth

| Tool | Role |
| --- | --- |
| **GitHub OAuth (App)** | Sign-in + higher API rate limits. Scope: `read:user` only (v0.9.5 dropped the write-granting `public_repo`; reading public data needs no repo scope). Never `repo` or `admin:*`. |
| **Server-side opaque sessions** | Cookie value is `secrets.token_urlsafe(32)`; server looks the row up directly. Chosen over JWT in v0.5.0 to keep revocation cheap and access tokens server-side. |
| **AES-GCM at rest** | GitHub access tokens encrypted in the `sessions` table with `SESSION_TOKEN_ENC_KEY`. Fresh 12-byte nonce per row; key rotation invalidates every session by design. |

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
| Frontend + Backend | **Vercel multi-service project** | One Vercel project hosts both via `experimentalServices` in the root `vercel.ts` (frontend at `/`, backend mounted at `/_/backend/*`). Typed via `@vercel/config/v1` since v0.8.7. Locked 2026-05-15. |
| Compute | **Vercel Functions (Fluid Compute)** | Function instances reused across concurrent requests, ~300s default timeout. Native marketplace integration with Neon. |
| DB | **Neon** | Vercel Marketplace integration. Auto-injects `DATABASE_URL` + variants. |
| Cache | **Upstash Redis** | User-provisioned account (not Marketplace). `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` pasted into Vercel env manually. |
| DNS / domain | Vercel-managed | Custom domain decided pre-v1.0 |

---

## Observability

| Tool | Role | Slice |
| --- | --- | --- |
| **Sentry (`@sentry/nextjs` + `sentry-sdk[fastapi]`)** | Error tracking (frontend + backend). Permanent free tier — 5K errors/mo + 50 replays/mo. PII scrubbed via `before_send` hook (GitHub tokens, OAuth secrets, encrypted session bytes, Cookie/Authorization headers). | v0.8.0 |
| **PostHog (`posthog-js` + `posthog-python` if needed)** | Product analytics + real-user web vitals (LCP / CLS / INP capture via SDK autocapture). Permanent free tier — 1M events/mo + 5K replays/mo + 12-month retention. Picked over Vercel Speed Insights specifically for the 12-month retention. | v0.8.0 |
| **structlog** | Backend JSON logging with `request_id` contextvar binding. Pairs with Sentry's logging integration to tag every event with the same `request_id` that appears in the structured log. | v0.8.0 |
| **`@axe-core/cli`** | Accessibility audit baseline + regression tool. Run against the deployed preview URL. Free OSS. | v0.8.0 |
| Sentry alert rules | Triggered alerting on critical error rate. Deferred to a v0.8.x patch once a week of real-error baselines exist. | v0.8.x |

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
