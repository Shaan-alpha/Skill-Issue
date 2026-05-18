# Skill Issue

> Your GitHub profile is your real resume. Skill Issue reads it honestly.

**Skill Issue** is an AI-powered GitHub intelligence platform. Drop in a username and it analyzes repositories, engineering maturity, OSS contributions, coding discipline, and growth trajectory — then turns it into actionable feedback, a 100-point engineering score, and shareable "GitHub Receipts."

Engineering insight first. AI flavor second. Scoring is deterministic and explainable; AI only handles narrative, summaries, and humor.

---

## What it does

- **Profile analysis** — pinned repos, contribution rhythm, README quality, CI/CD, deployment maturity, testing culture, licence detection
- **Engineering score (100 pts)** — Repo Quality 30 · Engineering Maturity 20 · OSS/Collab 15 · Consistency 10 · Recruiter Signal 15 · Learning Trajectory 10
- **7-tier identity ladder** — Hobbyist · Student Builder · Entry-Level · Professional · Senior · Staff · Principal Engineer, with intra-tier sub-rank
- **Stackable badges** — OSS Contributor, PR Master, Maintainer, Star Magnet, Polyglot, Long-haul, Indie Hacker, Toolmaker (signal-driven, deterministic, multi-earnable)
- **Tier-gated depth** — higher tiers unlock richer signals (licence SPDX, CI workflows, README quality, PR review depth, commit-message quality, cross-repo refactor)
- **Analysis modes (v0.4.0+)** — Roast, Mentor, Recruiter, CTO, Career
- **GitHub Receipts™ (v0.7.0+)** — shareable scorecards for LinkedIn, X, portfolios

---

## Status

Pre-alpha. Latest shipped release is **v0.5.0** (Auth + Persistence). Live at https://skill-issue-tau.vercel.app — GitHub OAuth sign-in, Neon Postgres persistence, `/me` history grid, opt-in `/share/[slug]` public links, signed-in ingestion uses each user's own GitHub rate-limit budget. The AI narrative layer (Roast + Mentor) now runs on **Groq** (`llama-3.3-70b-versatile`) by default — free tier, faster inference, OpenAI-compatible. Pre-existing OpenAI users can swap back by clearing `NARRATIVE_BASE_URL`. **v0.6.0 — Recruiter / CTO / Career modes** is the next slice. See [`CHANGELOG.md`](./CHANGELOG.md) for shipped slices, [`PLAN.md`](./PLAN.md) for the full roadmap, and [`docs/PROGRESS_LOG.md`](./docs/PROGRESS_LOG.md) for the most recent session handoff.

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
| [`docs/DEPLOY.md`](./docs/DEPLOY.md) | How to ship to Vercel (two-project layout) |
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

Verify: `curl http://localhost:8000/health` → `{"status":"ok","version":"0.5.0","db":"up"|"down"}`. (The `db` field reports DB reachability when `DATABASE_URL` is configured.)
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
cd frontend && npm run lint && npm run build
```

---

## License

See [`LICENSE`](./LICENSE).
