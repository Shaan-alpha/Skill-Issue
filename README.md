# Skill Issue

> Your GitHub profile is your real resume. Skill Issue reads it honestly.

**Skill Issue** is an AI-powered GitHub intelligence platform. Drop in a username and it analyzes repositories, engineering maturity, OSS contributions, coding discipline, and growth trajectory — then turns it into actionable feedback, a 100-point engineering score, and shareable "GitHub Receipts."

Engineering insight first. AI flavor second. Scoring is deterministic and explainable; AI only handles narrative, summaries, and humor.

---

## What it does

- **Profile analysis** — pinned repos, contribution rhythm, README quality, CI/CD, deployment maturity, testing culture
- **Developer category engine** — Student Builder, Entry-Level, Professional, Senior, OSS Contributor, Indie Hacker
- **Engineering score (100 pts)** — Repo Quality 30 · Engineering Maturity 20 · OSS/Collab 15 · Consistency 10 · Recruiter Signal 15 · Learning Trajectory 10
- **Analysis modes** — Roast, Mentor, Recruiter, CTO, Career
- **GitHub Receipts™** — shareable scorecards for LinkedIn, X, portfolios

---

## Status

Pre-alpha. Latest shipped release is **v0.2.0** (Frontend shell + backend hardening): Next.js 16 / React 19 app with landing + results route, schema-aligned types, CORS, username validation, error boundaries, and a fix for previously-dormant scoring signals (README / tests / CI / deployment detection). **v0.3.0 — AI narrative layer** is the next slice. See [`CHANGELOG.md`](./CHANGELOG.md) for shipped slices, [`PLAN.md`](./PLAN.md) for the full roadmap, and [`docs/PROGRESS_LOG.md`](./docs/PROGRESS_LOG.md) for the most recent session handoff.

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
cp .env.example .env        # then edit .env and add your GITHUB_TOKEN
uv run uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok","version":"0.2.0"}`.
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
