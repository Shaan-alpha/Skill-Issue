# skill-issue-backend

FastAPI backend for **Skill Issue** — ingests a GitHub profile and returns a deterministic 100-point engineering report.

See the repo root [`README.md`](../README.md), [`PLAN.md`](../PLAN.md), and [`ARCHITECTURE.md`](../ARCHITECTURE.md) for context.

## Local development

```bash
cd backend
uv sync
cp .env.example .env                                    # then edit .env
uv run uvicorn app.main:app --reload --port 8000
```

### Required env

| Var | Required for | Notes |
| --- | --- | --- |
| `GITHUB_TOKEN` | every `/analyze` request | Classic PAT or fine-grained token. Stored only in `.env` (gitignored). |
| `OPENAI_API_KEY` | `GET /narrative` | OpenAI-compatible API key. Use a Groq key when `NARRATIVE_BASE_URL` points at Groq. |
| `NARRATIVE_BASE_URL` | optional | OpenAI-compatible endpoint. Set to `https://api.groq.com/openai/v1` for Groq (default in production); empty for OpenAI. |
| `NARRATIVE_MODEL` | optional | Model id. Default: `llama-3.3-70b-versatile` (Groq). |
| `CORS_ALLOW_ORIGINS` | optional | Comma-separated allowed origins. Defaults to `http://localhost:3000`. |
| `CORS_ALLOW_ORIGIN_REGEX` | optional | Regex matched against `Origin` for preview deploys. |
| `DATABASE_URL` / `DATABASE_DIRECT_URL` | persistence routes (v0.5.0+) | Neon pooled (port 6543) + direct (5432) connections. |
| `GITHUB_OAUTH_CLIENT_ID` / `GITHUB_OAUTH_CLIENT_SECRET` / `OAUTH_REDIRECT_URL` | sign-in flow (v0.5.0+) | GitHub OAuth App credentials. |
| `SESSION_TOKEN_ENC_KEY` | sign-in flow (v0.5.0+) | 32-byte base64 key for AES-GCM at-rest token encryption. |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | optional (v0.7.0+) | Enables four-layer caching. Unset = in-process fallback for narrative + budget, every analyze runs cold. |

## Routes

| Route | Purpose |
| --- | --- |
| `GET /health` | Liveness — returns `{status, version, db, cache}`. |
| `GET /analyze/{username}` | Full ingestion → scoring → report. **Cached for 6h** (v0.7.0). Returns 400 (invalid username), 404 (no such GitHub user), 502 (GitHub upstream error), or 500. |
| `GET /narrative/{username}?mode={roast\|mentor}` | SSE streaming narrative. Cache shared across instances via Upstash when configured. |
| `GET /auth/{login,callback,logout}` | GitHub OAuth flow (v0.5.0). |
| `GET /me`, `GET /me/analyses` | Authenticated user info + paginated history (v0.5.0). |
| `POST/DELETE /analyses/{id}/share` | Toggle a public share slug (v0.5.0). |
| `GET /share/{slug}` | Read-only public view of a shared analysis. |

```bash
curl http://localhost:8000/health
curl http://localhost:8000/analyze/octocat
curl -N "http://localhost:8000/narrative/octocat?mode=roast"
```

## Tests

```bash
uv run pytest -v
```

Many test files need a Postgres test DB:

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/skill_issue_test
```

Without it, DB-fixture tests error (not fail) — every other test still runs.

Layout:
- `tests/test_health.py`, `tests/test_models.py`, `tests/test_settings.py`, `tests/test_dependencies.py` — basic plumbing
- `tests/github/test_client.py` + `test_client_cache.py` — REST + GraphQL + rate-limit retry + cache integration (respx-mocked)
- `tests/test_ingestion.py` — Profile assembly
- `tests/scoring/test_*.py` — one file per scorer, fixture-driven; plus `test_tiers.py`, `test_badges.py`, `test_depth.py` for the v0.3.0 tier ladder, badges, and depth dispatch
- `tests/test_analyze_e2e.py` — full ASGI route exercise; regression guard
- `tests/test_report_cache.py`, `tests/test_cache_integration.py` — v0.7.0 Report cache + end-to-end fault-injection
- `tests/cache/` — `RedisCache`, `singleflight`, key helpers (v0.7.0)
- `tests/narrative/test_*.py` — in-process LRU cache, daily budget, LLM streaming, SSE route, prompt digest locking; `test_cache_redis.py` + `test_budget_redis.py` cover the v0.7.0 Redis backends
- `tests/auth/`, `tests/db/`, `tests/persistence/`, `tests/routers/` — v0.5.0 OAuth + SQLAlchemy + persistence

## Lint + format

```bash
uv run ruff check .
uv run ruff format .
```

Config in `ruff.toml` — py312, line length 100, `E/F/I/UP/B/SIM/TCH/RUF`.

## Deploy

See [`../docs/DEPLOY.md`](../docs/DEPLOY.md) for the Vercel walkthrough. Since v0.5.0 the backend ships in the same Vercel project as the frontend (multi-service via `experimentalServices` in the root `vercel.json`); the deploy reads `backend/pyproject.toml` via `uv` — no derived `requirements.txt`.
