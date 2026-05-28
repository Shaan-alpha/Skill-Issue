# Deploy

> How to ship **Skill Issue** to Vercel. Updated for the v0.5.0 single-Vercel-project layout + v0.7.0 Upstash caching.

## Current layout

**One Vercel project** hosts both services via `experimentalServices` in the root `vercel.ts` (typed config; migrated from `vercel.json` in v0.8.7). Locked 2026-05-18.

| URL prefix | Service | What it is |
| --- | --- | --- |
| `/` | `frontend` | Next.js 16 App Router |
| `/_/backend/*` | `backend` | FastAPI on Vercel Functions (Python 3.12) |

The previous two-project setup (`skill-issue-frontend` + `skill-issue-backend`) was retired in v0.5.0 — one project, one dashboard, one log stream.

## One-time setup

You only do this once. After it, every git push deploys a preview automatically; every push to `main` ships production.

### 1. Create the Vercel project

1. <https://vercel.com/new> → **Import Git Repository** → pick `Shaan-alpha/Skill-Issue`.
2. **Root Directory:** repo root (the `vercel.ts` at the root declares both services).
3. **Framework Preset:** Other (services declared in `vercel.ts`).
4. **Deploy.** Vercel reads `vercel.ts` → builds `frontend/` as Next.js, builds `backend/` as a Python function.

### 2. Provision the integrations

#### Neon Postgres (Marketplace integration — recommended)

1. Vercel dashboard → **Storage** → **Create** → **Neon**.
2. Connect to this project. Vercel auto-injects: `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `POSTGRES_URL`, `PGHOST`, `NEON_PROJECT_ID`.
3. Manually add `DATABASE_DIRECT_URL` as a copy of `DATABASE_URL_UNPOOLED` (the backend's `Settings.database_direct_url` reads it under that name).

#### Upstash Redis (manual — **not** Marketplace as of v0.7.0)

1. Create an account at https://console.upstash.com (free tier covers our load: 10k commands/day, 256MB).
2. Create a Redis database. Pick the region closest to your Vercel region (Washington, D.C. for `iad1`).
3. Open the database → **REST API** panel → copy `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`.
4. Vercel dashboard → **Settings** → **Environment Variables**. Add both to **Production** and **Preview**, marked **Sensitive**.

When the cache env vars are unset, the backend short-circuits every cache integration — the app still works, just without warm-cache benefits.

### 3. Register the GitHub OAuth App

1. https://github.com/settings/applications/new
2. Homepage URL: `https://<your-vercel-host>`
3. Authorization callback URL: `https://<your-vercel-host>/_/backend/auth/callback` (note the `/_/backend/` prefix — the multi-service deploy mounts the backend there).
4. Copy the Client ID and Client Secret.

### 4. Set the remaining env vars

In Vercel → **Settings** → **Environment Variables**, add (Production + Preview, marked Sensitive where applicable):

| Variable | Value | Sensitive? |
| --- | --- | --- |
| `GITHUB_TOKEN` | A GitHub PAT for anonymous-ingest fallback | ✅ |
| `GITHUB_OAUTH_CLIENT_ID` | from step 3 | ✅ |
| `GITHUB_OAUTH_CLIENT_SECRET` | from step 3 | ✅ |
| `OAUTH_REDIRECT_URL` | `https://<your-vercel-host>/_/backend/auth/callback` | ✅ |
| `SESSION_TOKEN_ENC_KEY` | 32 random bytes, base64. Generate: `python -c "import secrets,base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"` | ✅ |
| `COOKIE_SECURE` | `true` (HTTPS-only cookies in production) | — |
| `CORS_ALLOW_ORIGINS` | `https://<your-vercel-host>` | — |
| `NEXT_PUBLIC_BACKEND_URL` | `https://<your-vercel-host>/_/backend` | — |
| `NARRATIVE_MODEL` | `llama-3.3-70b-versatile` (Groq default) | — |
| `NARRATIVE_BASE_URL` | `https://api.groq.com/openai/v1` (or empty for OpenAI) | — |
| `OPENAI_API_KEY` | Your Groq API key (it's an OpenAI-compatible endpoint) | ✅ |
| `UPSTASH_REDIS_REST_URL` | from step 2 (Upstash) | ✅ |
| `UPSTASH_REDIS_REST_TOKEN` | from step 2 (Upstash) | ✅ |
| `CRON_SECRET` | 32+ byte random hex string. Vercel Cron injects `Authorization: Bearer ${CRON_SECRET}` on every fire; the backend's `require_cron_auth` constant-time-compares it. Unset = `POST /cron/refresh-saved-analyses` returns 503. Generate: `python -c "import secrets; print(secrets.token_hex(32))"`. (v0.8.1+) | ✅ |
| `FRONTEND_BASE_URL` | `https://<your-vercel-host>` (no trailing slash). **Backend env only.** Where the share-revalidate webhook POSTs to. Unset = webhook is a logged no-op; the 3600s `cacheLife` fallback absorbs revocations. (v0.8.6+) | — |
| `REVALIDATE_SECRET` | 32+ byte random hex string. **Both `frontend` and `backend` services**, same value byte-for-byte. Authenticates the backend → frontend webhook that busts `/share/[slug]` cache tags on every share toggle. Unset = webhook disabled; revocations only revalidate at the 3600s fallback. Generate: `python -c "import secrets; print(secrets.token_hex(32))"`. (v0.8.6+) | ✅ |
| `GH_INGEST_CONCURRENCY` | Max concurrent GitHub API calls per `ingest_profile` invocation. Default `8`. Backend env only. Raise if Layer A cache hit-rate is high and you want lower analysis latency; lower if you're hitting GitHub secondary rate-limit 403s. (v0.9.0+) | — |
| `INTERNAL_PROXY_SECRET` | 32+ byte random hex string. **Both `frontend` and `backend` services**, same value byte-for-byte. Lets the backend trust the real client IP the Next.js RSC forwards (`X-Client-IP`) for proxied anonymous `/analyze`. Unset = anonymous `/analyze` is **not** IP-limited (real visitors are never throttled by mistake); narrative + signed-in limits stay active. Generate: `python -c "import secrets; print(secrets.token_hex(32))"`. (v0.9.2+) | — |
| `ANALYZE_ANON_PER_IP_PER_HOUR` | Anonymous per-IP `/analyze` cap. Default `20`. Backend env only. (v0.9.2+) | — |
| `ANALYZE_USER_PER_HOUR` | Signed-in per-user `/analyze` cap. Default `60`. Backend env only. (v0.9.2+) | — |
| `NARRATIVE_ANON_PER_IP_PER_HOUR` | Anonymous per-IP `/narrative` cap. Default `30`. Backend env only. (v0.9.2+) | — |
| `NARRATIVE_USER_PER_HOUR` | Signed-in per-user `/narrative` cap. Default `90`. Backend env only. (v0.9.2+) | — |
| `DB_POOL_SIZE` | SQLAlchemy pool size per Fluid Compute instance. Default `5`. Backend env only. Raise only on confirmed pool exhaustion. (v0.9.4+) | — |
| `DB_MAX_OVERFLOW` | Extra connections beyond `DB_POOL_SIZE` under burst. Default `5`. Backend env only. (v0.9.4+) | — |

> **DB pool ceiling.** The Neon compute exposes ~105 usable connections (`max_connections` 112 - 7 `superuser_reserved_connections` on the current ~0.25 CU compute). The app connects through the PgBouncer pooler (`statement_cache_size=0`), which multiplexes many client connections onto few server ones — so the ceiling is heavily buffered. If ever switched to a direct connection, keep `(DB_POOL_SIZE + DB_MAX_OVERFLOW) × peak_instances < 105`.

### 5. Run the initial Alembic migration

The DB schema lives in `backend/migrations/`. Pulling the prod `DATABASE_DIRECT_URL` locally (or pasting it once into a shell session — don't persist it) is the safe way to run migrations:

```powershell
# PowerShell — one-shot, the env var dies with the shell:
$env:DATABASE_DIRECT_URL = "<paste DATABASE_URL_UNPOOLED from Vercel>"
cd backend
uv run alembic upgrade head
```

Or via `vercel env pull` if you don't have Sensitive vars locked down (they return empty strings by default for security).

After the first migration: every subsequent push that includes a new migration runs it automatically against Vercel's connected Neon branch — **wait, no.** We don't auto-run migrations. The agent or user runs `alembic upgrade head` manually as the immediately-next action after deploying schema-changing commits.

## Verifying a deploy

```bash
# Health — should report db=up and cache=up after Upstash is provisioned
curl https://<your-vercel-host>/_/backend/health
# -> {"status":"ok","version":"0.8.3","db":"up","cache":"up"}

# Anonymous analyze
curl https://<your-vercel-host>/_/backend/analyze/octocat

# OG image (auto-wired by Next 16 file convention)
curl -o /tmp/og.png https://<your-vercel-host>/u/octocat/opengraph-image
file /tmp/og.png  # PNG image data, 1200 x 630

# Narrative stream (SSE)
curl -N "https://<your-vercel-host>/_/backend/narrative/octocat?mode=roast"
```

If the analyze route 500s, hit `Vercel dashboard → Runtime Logs` for the backend service — the FastAPI traceback shows up there.

If the frontend results page shows the **Analysis failed** boundary:

1. Confirm `NEXT_PUBLIC_BACKEND_URL` is set correctly.
2. Confirm `GITHUB_TOKEN` is set on the backend.
3. Check `/health` reports `db=up` and `cache=up` (or `unconfigured` for cache — that's fine).

If a CORS error appears in the browser console:

1. Check `CORS_ALLOW_ORIGINS` matches the frontend origin exactly.
2. Vercel sometimes assigns preview deploys to subdomains; `CORS_ALLOW_ORIGIN_REGEX` covers that pattern.

## Cache verification (v0.7.0)

After Upstash is provisioned:

```bash
# Two consecutive analyze calls — second should be substantially faster
time curl -s -o /dev/null https://<your-vercel-host>/_/backend/analyze/octocat
time curl -s -o /dev/null https://<your-vercel-host>/_/backend/analyze/octocat
```

Cold call: ~5-8s. Warm call (cached): ≤200ms p95 target. If the warm call isn't fast, check `/health` for `cache: "up"` and verify the env vars survived the deploy.

## Known limits as of v0.8.3

- **No global rate limiting.** Anyone can hit `/analyze` and burn through the ingestion budget. The per-user 10/hour cap on `/me/refresh/{username}` (v0.8.2) is the only rate limit shipped today. Global IP-level limits + abuse heuristics are v0.9.0 territory (Beta hardening).
- **`/share/[slug]` is not ISR-cached.** Each shared-page view re-renders server-side. Tolerable at current scale, but v0.8.4 ships on-demand `revalidateTag` so the route can opt in to ISR without a revocation correctness gap.
- **Sentry source-map upload not wired.** Frontend stack traces in Sentry show minified function names — runtime capture still works, only symbolication is degraded. Lands in a v0.8.x patch once `SENTRY_AUTH_TOKEN` / `SENTRY_ORG` / `SENTRY_PROJECT` are provisioned.
- **Sentry alert rules not wired.** v0.8.0 ships the integration but not the thresholds; needs ~1 week of baseline data first. Patch lands when the data is in.
- **Custom domain** — pre-v1.0.

## What's intentionally not here

- A `requirements.txt` step — Vercel reads `backend/pyproject.toml` directly via `uv` since v0.5.0.
- The retired two-project layout — see git history for `feat/v0.5.0-auth-persistence` if you need to reconstruct it.
