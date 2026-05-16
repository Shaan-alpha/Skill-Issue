# Deploy

> How to ship **Skill Issue** to Vercel. Required reading for the v0.2.0 preview URL exit criterion (and for every later slice that touches deploy).

## Layout

Two separate Vercel projects, both pointing at this monorepo with different **Root Directory** settings:

| Vercel project | Root | What ships | Framework |
| --- | --- | --- | --- |
| `skill-issue-frontend` | `frontend/` | Next.js 16 app | Next.js (auto-detected) |
| `skill-issue-backend` | `backend/` | FastAPI on Vercel Functions (Python) | Other (uses `backend/vercel.json`) |

Two projects keeps deploys independent, simplifies framework detection, and matches the version slices in [`PLAN.md`](../PLAN.md). A monorepo single-project move is on the table when v0.5.0 brings shared auth, but premature for v0.3.0.

## One-time setup (~10 min)

You only do this once per project. After this, every git push deploys a preview automatically.

### Backend project

1. <https://vercel.com/new> → **Import Git Repository** → pick `Shaan-alpha/Skill-Issue`.
2. Configure:
   - **Project name:** `skill-issue-backend`
   - **Root Directory:** `backend`
   - **Framework Preset:** Other
   - **Build Command:** leave blank (Vercel reads `backend/vercel.json`)
3. **Environment Variables** (Production, Preview, *and* Development):
   - `GITHUB_TOKEN` — your GitHub PAT (the value currently in `backend/.env`).
   - `OPENAI_API_KEY` — your OpenAI API key for streaming Roast/Mentor modes.
   - `CORS_ALLOW_ORIGINS` — `http://localhost:3000,https://skill-issue-frontend.vercel.app`
   - `CORS_ALLOW_ORIGIN_REGEX` — `https://skill-issue-frontend(-[a-z0-9-]+)?\.vercel\.app` (allows every preview URL of the frontend project, nothing else on `vercel.app`).
4. **Deploy.** First deploy installs `backend/requirements.txt` and exposes `backend/api/index.py` (which re-exports the FastAPI app).
5. Copy the production URL — likely `https://skill-issue-backend.vercel.app`.

### Frontend project

1. <https://vercel.com/new> → **Import Git Repository** → same repo.
2. Configure:
   - **Project name:** `skill-issue-frontend`
   - **Root Directory:** `frontend`
   - **Framework Preset:** Next.js (auto-detected)
3. **Environment Variables** (Production + Preview):
   - `NEXT_PUBLIC_BACKEND_URL` — the backend production URL from the previous step.
4. **Deploy.**

## Ongoing flow

- Every push to `main` ships **production** on both projects.
- Every push to any other branch ships a **preview** on both projects.
- Backend preview URLs hit the frontend preview URLs through the `CORS_ALLOW_ORIGIN_REGEX` pattern — no per-deploy env-var dance needed.

## Updating `requirements.txt`

`backend/requirements.txt` is a derived artifact, regenerated from `pyproject.toml`:

```bash
cd backend
uv export --no-hashes --no-emit-project --no-dev --format requirements-txt > requirements.txt
```

Regenerate it whenever you add or remove a runtime dependency. Until v0.9.0 introduces CI to enforce this, the developer who bumps a dep is responsible for committing both files.

## Verifying a deploy

After both projects are deployed:

```bash
# Health check
curl https://skill-issue-backend.vercel.app/health
# -> {"status":"ok","version":"0.4.0"}

# Real analyze (warm; cold may take longer due to Python cold start)
curl https://skill-issue-backend.vercel.app/analyze/octocat

# Real narrative stream (SSE)
curl -N "https://skill-issue-backend.vercel.app/narrative/octocat?mode=roast"

# Frontend
open https://skill-issue-frontend.vercel.app
```

If the frontend results page shows the **Analysis failed** boundary:

1. Open the frontend deployment in the Vercel dashboard → **Runtime Logs**. The page throw should show the actual HTTP status from the backend.
2. Confirm `NEXT_PUBLIC_BACKEND_URL` is set on the frontend project and matches the backend URL.
3. Confirm the backend has `GITHUB_TOKEN` and `OPENAI_API_KEY` and isn't returning 500.

If the browser console shows a CORS error:

1. Check the backend's deployed `CORS_ALLOW_ORIGINS` and `CORS_ALLOW_ORIGIN_REGEX`.
2. Open the response in DevTools → Network → look at the `Access-Control-Allow-Origin` header.

## Known limits as of v0.4.0

- **First-paint LCP is bottlenecked by the GitHub ingestion** (~5–10s warm, longer on Vercel cold start; Senior+ profiles add another ~20–40 HTTP calls for tier-gated depth enrichment). This is fundamental until v0.8.0 adds Upstash Redis caching of `/analyze` responses. Lighthouse Performance will reflect this — that's why the explicit Lighthouse exit criterion now lives in v0.9.0 (Polish + observability).
- **No rate limiting.** Anyone can hit `/analyze` and burn through your GitHub token budget. v0.10.0 territory.
- **No auth.** Public read-only API. Add `read:user` GitHub OAuth in v0.5.0.

## What's intentionally not here yet

- **Neon Postgres + Upstash Redis** integration via the Vercel Marketplace — v0.5.0 (Postgres) and v0.8.0 (Redis).
- **Cron jobs** for background re-ingestion — v0.8.0.
- **Custom domain** — v1.0.0.
