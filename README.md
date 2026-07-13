<div align="center">

# Skill Issue

**Your GitHub profile is your real resume. Skill Issue reads it honestly.**

[![Version](https://img.shields.io/github/v/release/Shaan-alpha/Skill-Issue?style=for-the-badge&label=release&color=10b981)](https://github.com/Shaan-alpha/Skill-Issue/releases)
[![License](https://img.shields.io/github/license/Shaan-alpha/Skill-Issue?style=for-the-badge&color=475569)](./LICENSE)
[![Live preview](https://img.shields.io/badge/live-skillissue.tech-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://skillissue.tech)
[![Status](https://img.shields.io/badge/status-v1.0.0%20·%20live-10b981?style=for-the-badge)](https://skillissue.tech)

[![Next.js](https://img.shields.io/badge/Next.js%2016-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React%2019-149eca?style=for-the-badge&logo=react&logoColor=white)](https://react.dev/)
[![Tailwind](https://img.shields.io/badge/Tailwind%204-0ea5e9?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python%203.12-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Neon](https://img.shields.io/badge/Neon%20Postgres-00e699?style=for-the-badge&logo=postgresql&logoColor=000000)](https://neon.tech/)
[![Upstash](https://img.shields.io/badge/Upstash%20Redis-00e9a3?style=for-the-badge&logo=redis&logoColor=000000)](https://upstash.com/)
[![Groq](https://img.shields.io/badge/Groq%20LLM-f55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com/)

</div>

---

**Skill Issue** is an AI-powered GitHub intelligence platform. Drop in a username and it analyzes repositories, engineering maturity, OSS contributions, coding discipline, and growth trajectory — then turns it into actionable feedback, a 100-point engineering score, and shareable "GitHub Receipts."

Engineering insight first. AI flavor second. Scoring is deterministic and explainable; AI only handles narrative, summaries, and humor.

> **▶ Try it live — [skillissue.tech](https://skillissue.tech)** — analyze any GitHub profile in seconds. If it's useful, a ⭐ on the repo helps other devs find it.

---

## What it does

- **Profile analysis** — pinned repos, contribution rhythm, README quality, CI/CD, deployment maturity, testing culture, licence detection
- **Engineering score (100 pts)** — Repo Quality 30 · Engineering Maturity 20 · OSS/Collab 15 · Consistency 10 · Recruiter Signal 15 · Learning Trajectory 10
- **7-tier identity ladder** — Hobbyist · Student Builder · Entry-Level · Professional · Senior · Staff · Principal Engineer, with intra-tier sub-rank
- **Stackable badges** — OSS Contributor, PR Master, Maintainer, Star Magnet, Polyglot, Long-haul, Indie Hacker, Toolmaker (signal-driven, deterministic, multi-earnable)
- **Tier-gated depth** — higher tiers unlock richer signals (licence SPDX, CI workflows, README quality, PR review depth, commit-message quality, cross-repo refactor)
- **Analysis modes** — Roast + Mentor (canonical two; Recruiter / CTO / Career were dropped 2026-05-19)
- **GitHub Receipts™** — shareable 1200×630 OG scorecards for LinkedIn, X, Discord, portfolios
- **Warm-cache latency** — repeat `/analyze/{user}` p95 ≤ 200ms backed by Upstash Redis (v0.7.0+)

---

## Status

Now at **v1.0.2** — a security & hardening release: fixed the nightly refresh cron (Vercel fires GET; the handler was POST-only), patched 7 backend dependency CVEs, and added CSRF, supply-chain (Dependabot + CI SCA gate), and HTTP-header hardening. (v1.0.1 was the operational launch-ops milestone — the skillissue.tech domain cutover, tracked in [`docs/LAUNCH.md`](./docs/LAUNCH.md).) **v1.0.0** was the first stable release (homepage link-preview cards, an autofocused search, an inline "analyze another" search on reports, and repo cleanup). v0.9.8 before it added launch landing sections — example reports, a "how it works" methodology section, and a GitHub-star CTA; v0.9.7 added a Privacy Policy and Terms of Service, linked from a new site-wide footer; v0.9.6 added a reusable load-test harness for the warm `/analyze` path (full 100 RPS run is an operator step); v0.9.5 ran a full pre-launch security audit — no high/critical findings — tightening the GitHub OAuth scope to read-only and adding HTTP security headers; v0.9.4 made the DB connection pool size env-tunable and genuinely fixed the back-nav search spinner; v0.9.3 added deletable `/me` history with undo, a golden "creator" scorecard for the project's creator account, and a first (incomplete) attempt at the back-nav spinner fix. Live at https://skillissue.tech — GitHub OAuth sign-in, Neon Postgres persistence, `/me` history, opt-in `/share/[slug]` public links. The AI narrative layer (Roast + Mentor) runs on **Groq** (`llama-3.3-70b-versatile`). v0.7.0 added Upstash Redis caching (warm `/analyze` ≤ 200 ms); v0.7.2 prod-certified the perf budget (CLS 0.080 → **0** structurally, perf 90 → 94, LCP 2,804 → 2,773 ms); v0.8.0 shipped Sentry (FE+BE), PostHog (events + web vitals), structlog JSON logging, on-voice 404, and a full axe a11y pass; v0.8.1 ships the nightly cron with bearer auth; v0.8.2 pairs it with the manual force-refresh button on `/me`; v0.8.3 hotfixes the empty-repo crash; v0.8.4 fixes the silent narrative misattribution; v0.8.5 closes the post-deploy-Sentry loop with a pre-merge CI gate; v0.8.6 closes v0.7.1's deferred share-page caching; v0.8.7 modernizes project config; v0.9.0 opens Beta hardening with bounded GH fan-out; v0.9.1 closes the /me N+1 + adds per-namespace Report cache versioning; v0.9.2 adds rate limiting (per-IP for anonymous, higher per-user caps for signed-in) on `/analyze` and `/narrative`; v0.9.3 adds deletable `/me` history with undo, attempts the back-nav search-spinner fix, and gilds the creator's scorecard. v0.9.4 makes the DB connection pool size env-tunable (defaults unchanged — RUM showed no pool exhaustion) and lands the real back-nav spinner fix (the v0.9.3 attempt addressed the wrong mechanism); v0.9.5 runs a full pre-launch security audit (no high/critical findings), tightens the OAuth scope to `read:user`, and adds HTTP security headers; v0.9.6 adds a reusable load-test harness for the warm `/analyze` path (the full 100 RPS run is an operator step); v0.9.7 adds a Privacy Policy and Terms of Service, linked from a new global footer; v0.9.8 adds launch landing sections (example reports, a how-it-works section, a GitHub-star CTA); **v1.0.0 is the first stable release** (homepage Open Graph previews, autofocused + inline search, repo cleanup). Public launch — domain, posts, traffic watch — is tracked in [`docs/LAUNCH.md`](./docs/LAUNCH.md). See [`CHANGELOG.md`](./CHANGELOG.md) for shipped slices, [`PLAN.md`](./PLAN.md) for the full roadmap, and [`docs/PROGRESS_LOG.md`](./docs/PROGRESS_LOG.md) for the most recent session handoff.

---

## Documentation map

| File | Purpose |
| --- | --- |
| [`PLAN.md`](./PLAN.md) | Versioned roadmap — what ships in each v0.X.0 |
| [`CHANGELOG.md`](./CHANGELOG.md) | What has actually shipped, per Keep-a-Changelog |
| [`AGENTS.md`](./AGENTS.md) | **Required reading for every AI agent or human contributor** — the rules of engagement |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | System design + MCP ecosystem |
| [`docs/PRODUCT_VISION.md`](./docs/PRODUCT_VISION.md) | Personality, target users, scoring rubric, voice |
| [`docs/TECH_STACK.md`](./docs/TECH_STACK.md) | Every library, version pin, and why |
| [`docs/PROGRESS_LOG.md`](./docs/PROGRESS_LOG.md) | Running narrative log — what was done and why |
| [`docs/DEPLOY.md`](./docs/DEPLOY.md) | How to ship to Vercel (single multi-service project + Upstash + Neon walkthrough) |
| [`docs/superpowers/plans/`](./docs/superpowers/plans/) | TDD sub-plans for each version slice |

---

## Quick start

You need two terminals — the FastAPI backend and the Next.js frontend run side by side in dev.

### Backend (`:8000`)

```bash
cd backend
uv sync
cp .env.example .env        # then edit .env and add your GITHUB_TOKEN and OPENAI_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok","version":"1.0.0","db":"up"|"down","cache":"up"|"down"|"unconfigured"}`. The `db` field reports DB reachability when `DATABASE_URL` is configured; the `cache` field reports Upstash reachability (`unconfigured` when `UPSTASH_REDIS_REST_URL` isn't set — perfectly fine for local dev, the in-process fallback covers it).
Hit the analyzer: `curl http://localhost:8000/analyze/octocat`.

### Frontend (`:3000`)

```bash
cd frontend
npm install
npm run dev
```

The frontend reads `NEXT_PUBLIC_BACKEND_URL` from `frontend/.env.local` (defaults to `http://localhost:8000`).
Open <http://localhost:3000> and analyze a username.

### Tests + lint

```bash
cd backend && uv run pytest -v && uv run ruff check .
cd frontend && npm run lint && npm run test:run && npm run build
```

The frontend `test:run` invokes Vitest (added in v0.6.0). Backend tests use pytest + respx; DB-dependent tests need `TEST_DATABASE_URL` (local Postgres or a Neon dev branch).

---

## License

See [`LICENSE`](./LICENSE).
