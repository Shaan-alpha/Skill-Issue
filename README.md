<div align="center">

# Skill Issue

**Your GitHub profile is your real resume. Skill Issue reads it honestly.**

[![Version](https://img.shields.io/github/v/release/Shaan-alpha/Skill-Issue?style=for-the-badge&label=release&color=10b981)](https://github.com/Shaan-alpha/Skill-Issue/releases)
[![License](https://img.shields.io/github/license/Shaan-alpha/Skill-Issue?style=for-the-badge&color=475569)](./LICENSE)
[![Live preview](https://img.shields.io/badge/live-skill--issue--tau.vercel.app-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://skill-issue-tau.vercel.app)
[![Status](https://img.shields.io/badge/status-pre--alpha-eab308?style=for-the-badge)](./PLAN.md)

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

Pre-alpha. Latest shipped release is **v0.8.5** (CI pipeline + `requirements.txt` cleanup — `.github/workflows/ci.yml` runs `pytest` + `ruff` + `npm lint/test/build` on every PR and every push to `main`; `requirements.txt` regenerated to carry all 15 direct deps instead of 6). Live at https://skill-issue-tau.vercel.app — GitHub OAuth sign-in, Neon Postgres persistence, `/me` history, opt-in `/share/[slug]` public links. The AI narrative layer (Roast + Mentor) runs on **Groq** (`llama-3.3-70b-versatile`). v0.7.0 added Upstash Redis caching (warm `/analyze` ≤ 200 ms); v0.7.2 prod-certified the perf budget (CLS 0.080 → **0** structurally, perf 90 → 94, LCP 2,804 → 2,773 ms); v0.8.0 shipped Sentry (FE+BE), PostHog (events + web vitals), structlog JSON logging, on-voice 404, and a full axe a11y pass; v0.8.1 ships the nightly cron with bearer auth; v0.8.2 pairs it with the manual force-refresh button on `/me`; v0.8.3 hotfixes the empty-repo crash caught by Sentry; v0.8.4 fixes the silent narrative misattribution; v0.8.5 closes the "regression caught only via post-deploy Sentry" loop with a pre-merge CI gate. **v0.8.6 — on-demand `revalidateTag` for `/share/[slug]` ISR** is next, then the `vercel.ts` migration (v0.8.7). See [`CHANGELOG.md`](./CHANGELOG.md) for shipped slices, [`PLAN.md`](./PLAN.md) for the full roadmap, and [`docs/PROGRESS_LOG.md`](./docs/PROGRESS_LOG.md) for the most recent session handoff.

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

Verify: `curl http://localhost:8000/health` → `{"status":"ok","version":"0.8.5","db":"up"|"down","cache":"up"|"down"|"unconfigured"}`. The `db` field reports DB reachability when `DATABASE_URL` is configured; the `cache` field reports Upstash reachability (`unconfigured` when `UPSTASH_REDIS_REST_URL` isn't set — perfectly fine for local dev, the in-process fallback covers it).
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
