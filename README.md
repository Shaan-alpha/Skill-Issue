<div align="center">

# Skill Issue

**Your GitHub profile is your real resume. Skill Issue reads it honestly.**

[![Version](https://img.shields.io/github/v/release/Shaan-alpha/Skill-Issue?style=for-the-badge&label=release&color=10b981)](https://github.com/Shaan-alpha/Skill-Issue/releases)
[![License](https://img.shields.io/github/license/Shaan-alpha/Skill-Issue?style=for-the-badge&color=475569)](./LICENSE)
[![Live](https://img.shields.io/badge/live-skillissue.tech-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://skillissue.tech)
[![Status](https://img.shields.io/badge/status-v1.0.10%20·%20live-10b981?style=for-the-badge)](https://skillissue.tech)

[![Next.js](https://img.shields.io/badge/Next.js%2016-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React%2019-149eca?style=for-the-badge&logo=react&logoColor=white)](https://react.dev/)
[![Tailwind](https://img.shields.io/badge/Tailwind%204-0ea5e9?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python%203.12-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Neon](https://img.shields.io/badge/Neon%20Postgres-00e699?style=for-the-badge&logo=postgresql&logoColor=000000)](https://neon.tech/)
[![Upstash](https://img.shields.io/badge/Upstash%20Redis-00e9a3?style=for-the-badge&logo=redis&logoColor=000000)](https://upstash.com/)
[![Groq](https://img.shields.io/badge/Groq%20LLM-f55036?style=for-the-badge&logo=groq&logoColor=white)](https://groq.com/)

**[▶ Try it live: skillissue.tech](https://skillissue.tech)**

Analyze any GitHub profile in seconds. Free, no signup required.<br/>
If it's useful, a ⭐ helps other devs find it.

</div>

---

Drop in a username. Skill Issue analyzes repositories, engineering maturity, OSS contributions, coding discipline, and growth trajectory, then turns it into actionable feedback, a 100-point engineering score, and a shareable "GitHub Receipt."

> **Engineering insight first, AI flavor second.** Scoring is deterministic and explainable. The AI only writes the narrative, summaries, and jokes; it never invents a number.

---

## What it does

| | |
| --- | --- |
| 🔍 **Profile analysis** | Pinned repos, contribution rhythm, README quality, CI/CD, deployment maturity, testing culture, licence detection |
| 💯 **Engineering score** | 100 points across six weighted signals: every point traceable to evidence |
| 🪜 **7-tier ladder** | Hobbyist → Student Builder → Entry-Level → Professional → Senior → Staff → Principal, with intra-tier sub-rank |
| 🏅 **Stackable badges** | OSS Contributor, PR Master, Maintainer, Star Magnet, Polyglot, Long-haul, Indie Hacker, Toolmaker: deterministic and multi-earnable |
| 🔓 **Tier-gated depth** | Higher tiers unlock richer signals: SPDX licence detection, CI workflows, PR review depth, commit-message quality, cross-repo refactor |
| 🔥 **Two voices** | **Roast Mode** for what a blunt senior would say · **Mentor Mode** for how to fix it |
| 🧾 **GitHub Receipts™** | Shareable 1200×630 scorecards for LinkedIn, X, Discord, portfolios |
| ⚡ **Fast on repeat** | Warm `/analyze/{user}` p95 ≤ 200 ms, backed by Upstash Redis |

### The scoring rubric

| Signal | Points | Question it answers |
| --- | --- | --- |
| Repo Quality | 30 | Do your repos look maintained: READMEs, tests, deploys, licences? |
| Engineering Maturity | 20 | Typed languages, CI pipelines, real architecture: not just scripts? |
| OSS & Collaboration | 15 | Do you ship into other people's codebases, or only your own? |
| Recruiter Signal | 15 | What a hiring manager sees in eight seconds: bio, pins, stars, links |
| Consistency | 10 | Commit rhythm over months: momentum, not a single sprint |
| Learning Trajectory | 10 | Are you levelling up? New stacks, bigger projects, year over year |

---

## Status

**v1.0.10: live** at [skillissue.tech](https://skillissue.tech), with GitHub OAuth sign-in, Neon Postgres persistence, `/me` history, and opt-in `/share/[slug]` public links.

Following the v1.0.0 stable launch, a security-hardening line ran from a full internal audit through v1.0.8, and CI-integrity work through v1.0.10.

| Release | What shipped |
| --- | --- |
| **v1.0.10** | Dependency-manifest drift guard: CI fails if `pyproject.toml` / `uv.lock` / `requirements.txt` disagree |
| **v1.0.9** | Audit-gate resilience: an advisory-registry outage warns instead of hard-blocking every PR |
| **v1.0.8** | Auth & endpoint hardening: session ids hashed at rest, Origin check on mutations, promotable CSP, `security.txt` + PR dependency review |
| **v1.0.7** | Version-display fix + low-severity hardening: secret repr-scrub, CORS-wildcard boot guard, cron-log trim, SSE done-sentinel |
| **v1.0.6** | Shared-token quota breaker: sheds new anonymous analyses before the shared GitHub token is exhausted |
| **v1.0.5** | Ingest amplification containment: per-analysis GitHub-call cap, request deadlines, LLM-budget refund on client abort |
| **v1.0.4** | Fail-closed cost controls: per-subject LLM budget, spoof-proof client IP, Sentry secret scrubbing, CI least-privilege |

<details>
<summary><b>Earlier history (v0.1.0 → v1.0.3)</b></summary>

- **v1.0.3** (hotfixed `/analyze` for hyper-active accounts tripping GitHub's GraphQL cost limit.
- **v1.0.2**) security & hardening: fixed the nightly refresh cron (Vercel fires GET; the handler was POST-only), patched 7 backend dependency CVEs, added CSRF, supply-chain (Dependabot + CI SCA gate) and HTTP-header hardening.
- **v1.0.1** (operational launch-ops milestone: the `skillissue.tech` domain cutover, tracked in [`docs/LAUNCH.md`](./docs/LAUNCH.md).
- **v1.0.0**) first stable release: homepage link-preview cards, autofocused search, inline "analyze another" on reports, repo cleanup.
- **v0.9.8** (launch landing sections: example reports, a how-it-works methodology section, a GitHub-star CTA.
- **v0.9.7**) Privacy Policy + Terms of Service, linked from a new site-wide footer.
- **v0.9.6** (reusable load-test harness for the warm `/analyze` path (the full 100 RPS run is an operator step).
- **v0.9.5**) full pre-launch security audit (no high/critical findings), OAuth scope tightened to `read:user`, HTTP security headers.
- **v0.9.4** (DB connection pool size made env-tunable (defaults unchanged; RUM showed no pool exhaustion) and the real back-nav spinner fix.
- **v0.9.3**) deletable `/me` history with undo, a golden "creator" scorecard, and a first (incomplete) back-nav spinner fix.
- **v0.9.2** (rate limiting on `/analyze` and `/narrative`: per-IP for anonymous, higher per-user caps when signed in.
- **v0.9.1**) closed the `/me` N+1 and added per-namespace Report cache versioning.
- **v0.9.0** (opened Beta hardening with bounded GitHub fan-out.
- **v0.8.7**) modernized project config (`vercel.json` → `vercel.ts`).
- **v0.8.6** (closed v0.7.1's deferred share-page caching.
- **v0.8.5**) closed the post-deploy-Sentry loop with a pre-merge CI gate.
- **v0.8.4** (fixed the silent narrative misattribution.
- **v0.8.3**) hotfixed the empty-repo crash.
- **v0.8.2** (manual force-refresh button on `/me`.
- **v0.8.1**) nightly cron with bearer auth.
- **v0.8.0** (Sentry (FE+BE), PostHog (events + web vitals), structlog JSON logging, on-voice 404, full axe a11y pass.
- **v0.7.2**) prod-certified the perf budget (CLS 0.080 → 0 structurally, perf 90 → 94, LCP 2,804 → 2,773 ms).
- **v0.7.0**: Upstash Redis caching (warm `/analyze` ≤ 200 ms).

Full detail in [`CHANGELOG.md`](./CHANGELOG.md); the roadmap lives in [`PLAN.md`](./PLAN.md).

</details>

---

## Documentation map

| File | Purpose |
| --- | --- |
| [`PLAN.md`](./PLAN.md) | Versioned roadmap: what ships in each slice |
| [`CHANGELOG.md`](./CHANGELOG.md) | What has actually shipped, per Keep-a-Changelog |
| [`AGENTS.md`](./AGENTS.md) | **Required reading for every AI agent or human contributor**: the rules of engagement |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | System design + MCP ecosystem |
| [`docs/PRODUCT_VISION.md`](./docs/PRODUCT_VISION.md) | Personality, target users, scoring rubric, voice |
| [`docs/TECH_STACK.md`](./docs/TECH_STACK.md) | Every library, version pin, and why |
| [`docs/PROGRESS_LOG.md`](./docs/PROGRESS_LOG.md) | Running narrative log: what was done and why |
| [`docs/DEPLOY.md`](./docs/DEPLOY.md) | How to ship to Vercel (multi-service project + Upstash + Neon walkthrough) |
| [`docs/OBSERVABILITY.md`](./docs/OBSERVABILITY.md) | Sentry, PostHog, structlog: what's wired and what to watch |
| [`docs/superpowers/plans/`](./docs/superpowers/plans/) | TDD sub-plans for each version slice |

---

## Quick start

Two terminals: the FastAPI backend and the Next.js frontend run side by side in dev.

### Backend (`:8000`)

```bash
cd backend
uv sync
cp .env.example .env        # then add your GITHUB_TOKEN and OPENAI_API_KEY
uv run uvicorn app.main:app --reload --port 8000
```

> **On the LLM key:** the client is OpenAI-compatible, so `OPENAI_API_KEY` is the variable name regardless of provider. Production points it at **Groq** (`openai/gpt-oss-120b`) via `NARRATIVE_BASE_URL` + `NARRATIVE_MODEL`; leave both unset to use OpenAI directly. The narrative layer is optional, scoring works without any LLM key.

Verify:

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"1.0.10","db":"up","cache":"unconfigured"}

curl http://localhost:8000/analyze/octocat
```

`db` reports DB reachability when `DATABASE_URL` is set. `cache` reports Upstash reachability; `unconfigured` is fine for local dev, the in-process fallback covers it.

### Frontend (`:3000`)

```bash
cd frontend
npm install
NODE_OPTIONS=--max-old-space-size=2048 npm run dev
```

> **Raise the heap.** Without `--max-old-space-size=2048`, `next dev` can OOM-crash on a cold compile.

The frontend reads `NEXT_PUBLIC_BACKEND_URL` from `frontend/.env.local` (defaults to `http://localhost:8000`). Open <http://localhost:3000> and analyze a username.

### Tests + lint

```bash
# backend — 359 tests; DB-fixture tests skip without TEST_DATABASE_URL
cd backend && uv run ruff check . && uv run ruff format --check . && uv run pytest -q

# frontend — 73 tests
cd frontend && npm run lint && npx tsc --noEmit && npm run test:run && npm run build
```

Backend tests use pytest + respx; the DB-dependent ones need `TEST_DATABASE_URL` (local Postgres or a Neon dev branch). Frontend tests run on Vitest.

---

## License

MIT, see [`LICENSE`](./LICENSE).
