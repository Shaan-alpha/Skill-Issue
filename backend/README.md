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
| `OPENAI_API_KEY` | `GET /narrative` | OpenAI API key for streaming Roast/Mentor modes. |
| `CORS_ALLOW_ORIGINS` | optional | Comma-separated allowed origins. Defaults to `http://localhost:3000`. |
| `CORS_ALLOW_ORIGIN_REGEX` | optional | Regex matched against `Origin` for preview deploys. Used in production to allow Vercel preview URLs. |

## Routes

| Route | Purpose |
| --- | --- |
| `GET /health` | Liveness + version |
| `GET /analyze/{username}` | Full ingestion → scoring → report. Returns 400 (invalid username), 404 (no such GitHub user), 502 (GitHub upstream error), or 500 (anything else, with traceback logged). |
| `GET /narrative/{username}?mode={roast\|mentor}` | SSE streaming endpoint. Token-by-token narrative breakdown. Includes LRU caching, daily budget limits, and deterministic on-voice fallbacks. |

```bash
curl http://localhost:8000/health
curl http://localhost:8000/analyze/octocat
curl -N http://localhost:8000/narrative/octocat?mode=roast
```

## Tests

```bash
uv run pytest -v
```

Layout:
- `tests/test_health.py`, `tests/test_models.py` — basic plumbing
- `tests/github/test_client.py` — REST + GraphQL + rate-limit retry (respx-mocked)
- `tests/test_ingestion.py` — Profile assembly
- `tests/scoring/test_*.py` — one file per scorer, fixture-driven
- `tests/test_analyze_e2e.py` — full ASGI route exercise; regression guard for the v0.1.0 crashes and the v0.3.0 shape change (`tier` + `badges`)
- `tests/scoring/test_tiers.py`, `tests/scoring/test_badges.py`, `tests/scoring/test_depth.py` — v0.3.0 tier ladder, 8 badges, tier-gated depth dispatch
- `tests/narrative/test_*.py` — v0.4.0 in-process LRU cache, daily budget, LLM streaming, SSE route, and prompt digest locking

## Lint + format

```bash
uv run ruff check .
uv run ruff format .
```

Config in `ruff.toml` — py312, line length 100, `E/F/I/UP/B/SIM/TCH/RUF`.

## Deploy

See [`../docs/DEPLOY.md`](../docs/DEPLOY.md) for the Vercel walkthrough. The deploy reads `backend/vercel.json`, exposes the FastAPI app via `backend/api/index.py`, and installs from `backend/requirements.txt` (regenerate via `uv export --no-hashes --no-emit-project --no-dev --format requirements-txt > requirements.txt`).
