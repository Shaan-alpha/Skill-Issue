# Load test harness

Open-loop load tester for the backend. Drives a target endpoint at a fixed RPS
and reports p50/p95/p99 latency, error rate, achieved throughput, and PASS/FAIL
against thresholds. Run from `backend/`:

```bash
uv run python loadtest/run.py --help
```

> **Windows / Git Bash note:** a bare `--path /health` argument gets mangled by
> MSYS into a Windows path (corrupting the URL). Prefix the command with
> `MSYS_NO_PATHCONV=1`, or run it from PowerShell, or use `--path=//health`.

## Quick sanity check (no Docker, no cache)

Start the backend, then hit a cheap endpoint to confirm the harness works.
Locally there's usually no `DATABASE_URL`, so `/health` blocks ~20 s per request
on a doomed DB ping — use `/openapi.json` instead for a clean check:

```bash
uv run uvicorn app.main:app --port 8000   # terminal 1
uv run python loadtest/run.py --target http://localhost:8000 --path /openapi.json \
  --rps 10 --duration 5 --warmup 1 --p95-ms 1000   # terminal 2
```

Expect `errors=0` and `RESULT: PASS`.

## Full warm-`/analyze` 100 RPS run (local)

The warm path needs a populated Report cache. `get_cache()` returns `None`
without Upstash, and real Upstash's free tier (~10k commands/day) can't absorb a
100 RPS run — so use a **local** Upstash-compatible Redis via SRH.

1. **Start a local Upstash-compatible Redis (SRH over Redis):**

   ```bash
   docker run -d --name si-redis -p 6379:6379 redis:7
   docker run -d --name si-srh -p 8079:80 \
     -e SRH_MODE=env -e SRH_TOKEN=local-token \
     -e SRH_CONNECTION_STRING="redis://host.docker.internal:6379" \
     hiett/serverless-redis-http:latest
   ```

2. **Start the backend pointed at SRH, with a real GitHub token, and the proxy
   secret UNSET** (so the analyze limiter skips anonymous enforcement):

   ```bash
   UPSTASH_REDIS_REST_URL=http://localhost:8079 \
   UPSTASH_REDIS_REST_TOKEN=local-token \
   GITHUB_TOKEN=<your_token> \
   uv run uvicorn app.main:app --port 8000
   ```
   (Ensure `INTERNAL_PROXY_SECRET` is **not** set in the environment, and send no
   session cookie — the harness is anonymous by default.)

3. **Run the load test** (the `--warmup` request cold-ingests once to prime the
   cache; the timed run is then pure cache hits):

   ```bash
   MSYS_NO_PATHCONV=1 uv run python loadtest/run.py \
     --target http://localhost:8000 --path /analyze/octocat \
     --rps 100 --duration 60 --warmup 1
   ```

4. **Find the knee** with a ramp:

   ```bash
   MSYS_NO_PATHCONV=1 uv run python loadtest/run.py --path /analyze/octocat \
     --ramp 50:100:200:400 --duration 30 --warmup 1
   ```
   Record the highest RPS stage that still PASSes (error rate < 1%, achieved
   RPS ≥ 95% of target, p95 under `--p95-ms`).

5. **Tear down:** `docker rm -f si-srh si-redis`.

## Pointing at a deployed target

```bash
uv run python loadtest/run.py --target https://<host>/_/backend --path /analyze/octocat --rps 100 --duration 30
```
Mind the cost (Vercel Active-CPU) and rate limits: a deployed backend with
`INTERNAL_PROXY_SECRET` set WILL rate-limit anonymous `/analyze` — sign in or
raise the limits for the window. Keep deployed runs short.

## Thresholds (PASS/FAIL)

- error rate `< --max-error-rate` (default 1%)
- achieved RPS `>= 95%` of `--rps`
- p95 latency `< --p95-ms` (default 250 ms; tune from the warm baseline)

Exit code is 0 on PASS, non-zero on FAIL.
