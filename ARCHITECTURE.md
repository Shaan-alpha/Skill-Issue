# Architecture

> System design for **Skill Issue**. Living document — update on every structural change. Companion to [`PLAN.md`](./PLAN.md) and [`docs/TECH_STACK.md`](./docs/TECH_STACK.md).

---

## Guiding principles

1. **Determinism before AI.** Every score is computed by code, not by an LLM. The LLM only writes prose around already-computed numbers.
2. **Stateless analyzers, cached results.** Scoring is a pure function of GitHub data. Caching lives at the edges (Redis + Postgres), not inside the scorers.
3. **Polite to GitHub.** Respect rate limits, prefer authenticated requests, use GraphQL when it saves N+1 round-trips, cache aggressively.
4. **Frontend renders facts.** The frontend never computes a score; it consumes a fully-formed report from the backend.
5. **MCP and plugins are the toolbox, not the product.** They accelerate development but are never load-bearing for users.

---

## High-level data flow

```
                     ┌────────────────────────────────────┐
                     │  User: enters github.com/username  │
                     └────────────────────────────────────┘
                                       │
                                       ▼
              ┌────────────────────────────────────────────────┐
              │ Next.js 16 App Router (frontend, Vercel)       │
              │  - Landing, analyze flow, results, receipts    │
              │  - Streams narrative via SSE (v0.4.0+)         │
              └────────────────────────────────────────────────┘
                                       │ HTTP / fetch
                                       ▼
              ┌────────────────────────────────────────────────┐
              │ FastAPI backend (Python 3.12, async)           │
              │  ┌──────────────────────────────────────────┐  │
              │  │ Ingestion layer (httpx + GraphQL)        │  │
              │  │   - profile, pinned, repos, commits,     │  │
              │  │     PRs, issues, langs, contribs         │  │
              │  └──────────────────────────────────────────┘  │
              │  ┌──────────────────────────────────────────┐  │
              │  │ Two-pass scoring engine (deterministic)  │  │
              │  │   pass 1: repo_quality(30) + maturity    │  │
              │  │   (20) + oss_collab(15) + consistency    │  │
              │  │   (10) + recruiter_signal(15) +          │  │
              │  │   trajectory(10) → base total → tier     │  │
              │  │   pass 2: tier-gated depth enrichment    │  │
              │  │   (licence / workflows / README /        │  │
              │  │   review depth / dep files / commit      │  │
              │  │   quality / cross-repo) → re-score       │  │
              │  └──────────────────────────────────────────┘  │
              │  ┌──────────────────────────────────────────┐  │
              │  │ Tier ladder + badges (deterministic)     │  │
              │  │   7 tiers (Hobbyist → Principal),        │  │
              │  │   intra-tier sub-rank, 8 stackable       │  │
              │  │   signal-driven badges                   │  │
              │  └──────────────────────────────────────────┘  │
              │  ┌──────────────────────────────────────────┐  │
              │  │ Narrative formatter (OpenAI, mode-aware) │  │
              │  │   - receives score JSON, never raw data  │  │
              │  │   - streams SSE back to frontend         │  │
              │  └──────────────────────────────────────────┘  │
              └────────────────────────────────────────────────┘
                                │              │
                  ┌─────────────┘              └────────────┐
                  ▼                                          ▼
        ┌──────────────────┐                   ┌─────────────────────┐
        │ Upstash Redis    │                   │ Neon Postgres        │
        │ - GH API cache   │                   │ - users               │
        │ - score cache    │                   │ - analyses + runs    │
        │ - narrative cache│                   │ - narratives          │
        │ - rate limits    │                   │ - share tokens        │
        └──────────────────┘                   └─────────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ GitHub OAuth     │
                       │ (auth + higher   │
                       │  rate limits)    │
                       └──────────────────┘
```

---

## Component breakdown

### Frontend — `frontend/` (Next.js 16)

- **App Router** for layouts, streaming, and partial prerendering. Bundler: **Turbopack** (Next 16 default).
- **Server Components** for the landing and shell; **Client Components** only where interactivity (mode toggle, animations, position-bar marker, badge tooltips) requires it.
- **shadcn/ui** as the component baseline; **Base UI** primitives (Progress, Tooltip) for accessible composition; **Framer Motion** with `LazyMotion` (`m` namespace) for orchestrated transitions.
- **Routes:**
  - `/` — landing
  - `/u/[username]` — results (tier ladder, position bar, badges, score matrix)
  - `/u/[username]/card` — shareable OG card render (v0.7.0)
  - `/me` — authenticated history (v0.5.0+)
  - `/api/*` — proxies and OG image generation only; analysis itself lives on FastAPI
- **State:** server-driven by default; React Query / SWR only where client polling/streaming demands it.

### Backend — `backend/` (FastAPI)

- **Layers:** `app/ingestion/`, `app/scoring/` (which contains `tiers.py`, `badges.py`, `depth.py`, `engine.py` + per-bucket scorers), `app/github/`, `app/narrative/` (v0.4.0), `app/db/` (v0.5.0), `app/cache/` (v0.8.0).
- **Concurrency:** `asyncio` end to end; `httpx.AsyncClient` for outbound; no blocking I/O in the request path.
- **GitHub access:** REST + GraphQL via a single typed client that handles rate-limit headers, retries with jitter, and conditional requests (`If-None-Match`).
- **Scoring contract:** every scorer is `def score(profile: Profile) -> ScoreResult` where `ScoreResult` carries `points: int`, `max_points: int`, and `evidence: list[Evidence]`. Evidence is what the UI displays under "Why this score" — never hand-waved.
- **Tier contract:** `assign_tier(total: int) -> TierInfo` returns `(name, sub_rank, band, prev_tier, next_tier, pts_to_next, pts_above_prev)`. Pure function of the integer total; no I/O.
- **Badge contract:** each detector is `(profile, breakdown) -> Badge | None`. Detectors compose via `compute_badges(profile, breakdown) -> list[Badge]`. Badges stack — no priority ordering.
- **Depth contract:** `enrich_for_tier(profile, base_tier, gh) -> None` mutates the profile with deeper signals appropriate to the base tier. All extra HTTP calls funnel through here and fan out via `asyncio.gather`. Per-call failures are swallowed; the base report is still valid.
- **Narrative contract:** narrative functions receive *only* the `Report` (scores + tier + badges + headline signals). They cannot see raw repos or commits. This prevents the LLM from inventing technical claims.

### Data — Neon Postgres

Schema sketch (finalized in v0.5.0):

- `users(id, github_id, login, avatar_url, created_at)`
- `analyses(id, user_id?, username, created_at, latest_run_id)`
- `analysis_runs(id, analysis_id, score_json, tier, sub_rank, badges_json, started_at, finished_at, github_etag)`
- `narratives(id, run_id, mode, text, model, cost_cents)`
- `share_tokens(id, analysis_id, token, expires_at)`

### Cache — Upstash Redis

- `gh:rest:{etag}` → response body (conditional revalidation)
- `gh:gql:{hash}` → response body (TTL 10m)
- `score:{username}:{etag-bundle}` → ScoreReport
- `narr:{username}:{mode}:{score-hash}` → narrative text
- `ratelimit:ip:{ip}` and `ratelimit:user:{id}` → token buckets

### Auth — GitHub OAuth

- Server-side OAuth code flow (no PKCE-only). State in httpOnly signed cookies.
- We request `read:user` and `public_repo` only. Never `repo` (we do not need private data) and never `admin:*`.
- Token storage: short-lived session JWT containing user id; the actual GitHub token is encrypted at rest and used only server-side.

### AI — OpenAI

- Client wrapped behind `narrative/llm.py` so swapping providers (Anthropic, local) is a single-file change.
- Default model: latest GPT class for narrative; cheap small model for short summaries.
- Strict prompt templates per mode; all prompts version-controlled and regression-tested.
- Cost guardrails: per-request budget, per-day project budget, alerting via Sentry.

---

## MCP and plugin ecosystem (development tooling)

These are **development-time accelerators**, not runtime dependencies. None of them ship to users.

| MCP / Plugin | Role | When to use |
| --- | --- | --- |
| **GitHub MCP** | Repository intelligence | Anywhere we'd otherwise hand-call `gh` — PRs, issues, repo inspection during dev |
| **Context7** | Live framework docs | Before guessing Next.js / React / FastAPI / shadcn API usage |
| **Playwright MCP** | UI automation | Visual verification of frontend changes; OG card render checks |
| **Postgres MCP** | DB intelligence | Schema inspection, query plans during scoring tuning |
| **Figma MCP** | Design ↔ code sync | When importing layout / typography / spacing from design files |
| **Sequential Thinking MCP** | Structured reasoning | Large architectural decisions, scorer design |
| **Vercel plugin (`vercel:*` skills)** | Deploy + env + storage | Anything Vercel-side: deploys, env pulls, marketplace, OG, runtime cache |
| **shadcn skill** | Component install / theming | Adding or composing shadcn primitives |
| **Filesystem MCP** | Bulk edits | Cross-file refactors, structural moves |

> **Rule:** New MCPs and plugins require user approval before install. See rule 5 in [`AGENTS.md`](./AGENTS.md).

---

## Deployment topology (target)

- **Frontend:** Vercel (Next.js 16 native).
- **Backend:** **Vercel Functions (Fluid Compute)** — locked 2026-05-15. Same dashboard as the frontend, OIDC env handoff, native marketplace integration with Neon + Upstash. Implications we will design around:
  - Function duration caps → ingestion must stream progress and avoid cold-path > 5min work; long re-ingestion runs in v0.8.0 use Vercel Cron + chunked work, not a single long invocation.
  - Cold starts → keep imports lean in the request path; warm critical routes with cron pings if needed.
  - Python on Vercel is fully supported but second-class vs. Node — pin runtime versions explicitly in `vercel.json`.
- **DB:** Neon Postgres (branch-per-PR for migrations).
- **Cache:** Upstash Redis (region-paired with backend).
- **Secrets:** Vercel env + 1Password references. Never committed.

---

## Open architecture questions

These are explicitly unresolved. Decisions get logged in [`docs/PROGRESS_LOG.md`](./docs/PROGRESS_LOG.md) when made.

1. **ORM** — SQLModel vs. SQLAlchemy + Alembic vs. Drizzle (if Node-side). Decision in v0.5.0.
2. **Streaming framework** — SSE vs. WebSocket vs. Vercel AI SDK helpers. Decision in v0.4.0.
3. **Background ingestion** — cron on Vercel vs. Inngest vs. self-hosted. Decision in v0.8.0.
4. **OG image runtime** — `@vercel/og` (edge) vs. Satori-on-Node. Decision in v0.7.0.
