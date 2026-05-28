# Changelog

All notable changes to **Skill Issue** are recorded here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every version listed here must correspond to a slice in [`PLAN.md`](./PLAN.md) whose exit criteria have been met.

---

## [0.9.5] — 2026-05-28

### Security
- **Full pre-launch security review — no high or critical findings.** Authorization (ownership checks on every mutation), session encryption, OAuth CSRF protection, SQL-injection safety, output escaping, and SSRF protection on user-supplied input were all verified sound.

### Changed
- **Tightened the GitHub sign-in permission to read-only.** Sign-in previously requested a scope that technically allowed writing to your public repositories; it now requests read-only access only, since Skill Issue exclusively reads public data. (Existing sessions are unaffected; the narrower permission applies on next sign-in.)
- **Added HTTP security headers** (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`) plus a report-only Content-Security-Policy as a baseline for hardening before public launch.

---

## [0.9.4] — 2026-05-28

### Changed
- **Database connection pool size is now configurable** via the `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` environment variables (defaults unchanged at 5 each), so it can be tuned in production without a redeploy. Telemetry showed no connection-pool pressure at current scale, so this ships the capability without changing the running defaults.

### Fixed
- **Search button no longer sticks on a spinner after pressing browser Back.** Returning to the landing page from a report could leave the analyze button spinning and its input disabled. The v0.9.3 attempt fixed the wrong mechanism; this is the real fix.

---

## [0.9.3] — 2026-05-28

### Added
- **Delete saved analyses.** Each card on your history page (`/me`) now has a ✕ to remove an analysis, with a brief **Undo** in case you change your mind.
- **Creator flair.** The project's creator account gets a distinguished golden scorecard (gold ring, chips, and badges) and a "CREATOR · SKILL ISSUE" tag — on the report page and the shareable card, so the person who built Skill Issue is recognizable on their own report.

### Fixed
- **Stuck search spinner.** After analyzing a profile and pressing the browser Back button, the landing-page search button could stay stuck spinning (and the input disabled). It now resets correctly when the page is restored.

---

## [0.9.2] — 2026-05-27

### Added
- **Rate limiting on analysis and narrative requests.** Anonymous visitors are limited per IP; signed-in users get a higher per-account limit (they analyze with their own GitHub token). Exceeding a limit returns a clear, on-voice "slow down" page with a retry hint instead of a generic error. Defaults: 20 analyses / 30 narratives per hour for anonymous visitors, 60 / 90 for signed-in users — all tunable via env vars without a redeploy.

### Changed
- The internal rate-limit counter is now keyed by a generic subject (`user:<id>` or `ip:<addr>`), shared across the force-refresh, analyze, and narrative limits.

### Notes
- New env var `INTERNAL_PROXY_SECRET` (set the same value on the frontend and backend) lets the site attribute analysis requests to the real visitor IP rather than the server's. Until it's set, anonymous analysis is **not** IP-limited — so real visitors are never throttled by mistake — while narrative and signed-in limits stay active.
- All cache layers remain fail-open: if Redis is unavailable, requests are allowed rather than blocked.

---

## [0.9.1] — 2026-05-27

### Fixed
- **`/me/analyses` N+1 query.** The list endpoint was issuing one `SELECT AnalysisRun` per row inside the serializer loop (21 round-trips per 20-row page). `list_user_analyses` already JOINed `AnalysisRun` via `latest_run_id` but was discarding the join result; it now returns `tuple[list[tuple[Analysis, AnalysisRun | None]], int]` so the route consumes the joined row directly. Net: 1 query per page instead of 1+N. No JSON contract change.

### Added
- **`REPORT_SCHEMA_VERSION` constant** in `app/cache/keys.py`. Layer A Report cache keys now carry a per-namespace version prefix: composed key shape is `si:v1:report:v1:<lowercased-username>`. Bumping `REPORT_SCHEMA_VERSION` on future `Report`-shape changes invalidates only the report namespace — no more silent ~6h of cross-namespace Pydantic validation warnings on every schema bump, and no need to bump global `KEY_PREFIX` (which would nuke GH/narrative/lock/budget caches too).

### Notes
- Existing `si:v1:report:<username>` keys orphan in Upstash until their 6h TTL expires. No manual cache purge needed; the new keys win on first request, and old keys GC at TTL with bounded memory cost.
- The `Analysis` model is unchanged. The N+1 fix is purely at the persistence/router layer; no new relationship, no new query path.

---

## [0.9.0] — 2026-05-26

### Added
- **Bounded GitHub fan-out in `ingest_profile`.** A new per-call `asyncio.Semaphore(settings.gh_ingest_concurrency)` (default 8) wraps both `asyncio.gather` blocks — the up-to-20 root-contents enrichment and the up-to-10 commit-history fetch. A single analysis can no longer burst past GitHub's secondary rate-limit threshold, and anonymous-token sharing scales to more analyses/hr before the 5000/hr ceiling bites. Sequential `list_languages` loop is intentionally untouched (already bounded by construction; parallelizing it would *increase* peak concurrent for the same cost). Opens the v0.9.x Beta hardening family.
- **`GH_INGEST_CONCURRENCY` env var** (optional, default `8`). Tune in prod without redeploy: raise if Layer A cache hit-rate is high and you want lower analysis latency; lower if you're hitting 403s. Backend env only.

### Tests
- 2 new in `tests/test_ingestion.py` against a `FakeGitHubClient` that records max in-flight calls across a 50-repo synthetic profile. Default-cap test asserts `max_in_flight ≤ 8`; override-cap test (`Settings(gh_ingest_concurrency=2)` via monkeypatch) asserts `max_in_flight ≤ 2`. Suite: 261 → 263 non-DB-fixture pass.

### Notes
- This is the first slice of the v0.9.x Beta hardening family. Decomposed 2026-05-26 into: bounded fan-out (this) → `/me/analyses` N+1 + Layer A cache schema version → DB pool tune → rate limiting + abuse heuristics → security review + load test → legal docs. Each slice is shippable in isolation.
- Tail latency on heavy profiles increases by ~500ms on a cold cache (3 batches of 8 instead of 1 batch of 20). Layer A's 6h Report cache absorbs this cost — first hit per user pays it once, subsequent hits are sub-200ms. RUM via PostHog (v0.8.0) will surface real-user impact post-deploy.
- `_gated` uses Python 3.12 PEP 695 generic syntax (`async def _gated[T](sem, coro)`) instead of legacy `TypeVar` — eliminates one import + satisfies ruff `UP047`.

---

## [0.8.7] — 2026-05-26

### Changed
- **Root project configuration migrated from `vercel.json` to typed `vercel.ts`.** Uses `@vercel/config/v1`'s `VercelConfig` type so a typo in `experimentalServices`, `crons`, or `git.deploymentEnabled` is caught at typecheck time instead of at deploy time. No behavioral change — same two services (`frontend` Next.js, `backend` FastAPI), same nightly cron at `03:00 UTC`, same branch-deploy filter blocking `feat/*`, `fix/*`, `chore/*`, `docs/*`, `ops/*`, `style/*`, `refactor/*`, `test/*` from auto-deploying. Tracks Vercel's 2026-02-27 recommended config form.

### Added
- **Root `package.json`** (`private: true`) holding `@vercel/config` and `typescript` as devDeps. Lets Vercel resolve the typed config at build time and lets local/CI `tsc` typecheck `vercel.ts` standalone.
- **Root `tsconfig.json`** scoped to `vercel.ts` only — no JSX, no DOM lib, no project references. Independent of the frontend's tsconfig.
- **CI job** `Config (vercel.ts typecheck)` in `.github/workflows/ci.yml` runs `npm ci` + `npx tsc --noEmit -p .` so config regressions fail pre-merge.

### Removed
- **Root `vercel.json`.** Replaced by `vercel.ts`. (`backend/vercel.json` is unchanged — per-function static config has no logic to type.)

### Notes
- `@vercel/config@0.5.0` already types `experimentalServices` on `VercelConfig` — the spec's planned file-local intersection-type fallback was not needed. Migration shipped as a clean `export const config: VercelConfig = { … }` literal.
- `npm audit` reports three high-severity advisories in `@vercel/config`'s transitive `path-to-regexp` via `@vercel/routing-utils`. Runtime blast radius is zero — `@vercel/config` is a devDep that only executes inside Vercel's build pipeline parsing our static config; `npm audit --omit=dev` reports clean. `npm audit fix --force` would downgrade to `0.0.32` (two minors back) — accepting the advisory until Vercel publishes a patched upstream.

---

## [0.8.6] — 2026-05-25

### Added
- **`/share/[slug]` Partial Prerendering via Next 16 Cache Components.** Public share pages now serve from a per-slug cache tagged `share:<slug>`. Backend share-toggle endpoints (`POST /analyses/{id}/share` and `DELETE /analyses/{id}/share`) schedule a fire-and-forget webhook to a new frontend route `POST /api/revalidate`, which calls `revalidateTag(tag, { expire: 0 })` for immediate invalidation. A revoked slug 404s on the next request — no stale window. Closes v0.7.1's deferred share-page caching.
- **Backend `app/share/webhook.py::revalidate_share_slug(slug)`** — fire-and-forget POST to `${FRONTEND_BASE_URL}/api/revalidate` with `X-Revalidate-Secret` header and `{tag: "share:<slug>"}` body. 5s timeout. All failures (4xx, timeout, network) logged + swallowed — never blocks the toggle's HTTP response. Reads through `settings_module.settings` so test reassignment is observed at call time.
- **Backend `share_analysis` + `revoke_share` schedule the webhook via FastAPI `BackgroundTasks`** so it fires after the response is sent. Empty-removed-slug case (already-revoked) intentionally skips scheduling.
- **`revoke_share_slug` now returns the removed slug `str`** (was `None`) so the caller can pass it to the webhook. Empty string when nothing was shared.
- **Frontend `POST /api/revalidate` route.** Constant-time `crypto.timingSafeEqual` against `process.env.REVALIDATE_SECRET`. Tag regex `^share:[A-Za-z0-9_-]{1,64}$` prevents the endpoint from being a generic revalidation gadget even if the secret leaks. Returns 401 on missing/wrong secret, 400 on bad tag, 204 on success.
- **`next.config.ts` enables `cacheComponents: true`** — required for `'use cache'` directive support and PPR.
- **`og-card-data.ts::fetchSharedPayload(slug)`** — `'use cache'` + `cacheTag(\`share:${slug}\`)` + `cacheLife({ revalidate: 3600 })`. 3600s fallback bounds staleness if the webhook ever silently fails. `fetchReportForSlug` now delegates to this so the OG image route (`/share/[slug]/opengraph-image.tsx`) automatically shares the same cache + invalidation as the page.
- **Two new env vars:** `FRONTEND_BASE_URL` (backend only) and `REVALIDATE_SECRET` (both sides; constant-time compared). Either unset → graceful degradation: the 3600s `cacheLife` absorbs the gap.

### Changed
- **`/share/[slug]/page.tsx` migrates from `force-dynamic` to PPR.** The data fetch lives in a `<Suspense>`-wrapped child component (`SharedContent`); `await params` happens inside that boundary so the page shell prerenders cleanly. Build output confirms `◐ Partial Prerender` treatment. A new `SharedSkeleton` provides the suspense fallback.
- **`/me/page.tsx` and `/u/[username]/card/page.tsx` drop `force-dynamic`** — incompatible with `cacheComponents: true`. Both pages remain auto-dynamic via existing `cookies()` / `params` consumption; no behavior change.
- **`tests/test/setup.ts` stubs `next/cache`** (`cacheTag` / `cacheLife` / `revalidateTag`) as no-ops in vitest — they throw outside the Next runtime when `cacheComponents` is enabled.

### Tests
- 5 backend webhook tests via respx (`tests/share/test_webhook.py`): unconfigured no-op, happy path request shape, 4xx swallow, timeout swallow, tag prefix guarantee.
- 1 DB-fixture persistence test asserting `revoke_share_slug` returns the removed slug + `""` on double-revoke.
- 3 DB-fixture share-router tests asserting `BackgroundTasks.add_task` scheduling for POST (new slug), DELETE (just-removed slug), and double-DELETE-doesn't-schedule.
- 5 frontend vitest cases for `/api/revalidate`: 401 missing secret, 401 wrong secret, 400 missing tag, 400 bad-prefix tag, 204 + `revalidateTag` call shape (asserting `{ expire: 0 }`).
- Suite: 256 → 261 non-DB backend (5 webhook). 37 → 42 frontend vitest.

### Provisioning gate (before tagging)
- Generate `REVALIDATE_SECRET` via `python -c "import secrets; print(secrets.token_hex(32))"`. Paste into Vercel as **Sensitive** on **both** `frontend` and `backend` services, Production + Preview. Same value byte-for-byte.
- Set `FRONTEND_BASE_URL=https://skill-issue-tau.vercel.app` on the **backend** service env (no trailing slash), Production + Preview.

### Notes
- The webhook is fire-and-forget by design: failure to invalidate logs + Sentry-tags but never affects the share toggle's user-facing response. Worst case under sustained webhook failure is up to 1 hour of stale read until the `cacheLife` fallback fires.
- 404 results are NOT cached, so a re-share with a brand-new slug works on first hit without manual cache priming.

---

## [0.8.5] — 2026-05-25

### Added
- **CI pipeline** — `.github/workflows/ci.yml` runs on every pull request and every push to `main`. Backend job: `uv sync --frozen --dev` → `ruff check .` → `ruff format --check .` → `pytest -q` (non-DB-fixture path; the DB-fixture suite still requires `TEST_DATABASE_URL` against a Neon branch and is left as a separate Vercel-deploy-side check). Frontend job: `npm ci` → `npm run lint` → `npx tsc --noEmit` → `npm run test:run` → `npm run build` (with `NEXT_PUBLIC_BACKEND_URL=http://ci-placeholder` so module-level env reads don't crash the build). Concurrency group cancels stale in-progress runs when a new push lands on the same ref. Pairs naturally with v0.8.3's "regression caught only post-deploy via Sentry" lesson — that loop now closes pre-merge.

### Fixed
- **`backend/requirements.txt` was missing 9 of 15 direct runtime deps** (`alembic`, `asyncpg`, `authlib`, `cryptography`, `openai`, `sentry-sdk`, `sqlalchemy`, `structlog`, `upstash-redis`). Production survived only because `@vercel/python` resolves through `pyproject.toml` + `uv.lock`; any developer/contributor / Docker build / CI matrix using `pip install -r requirements.txt` would have produced a broken environment. Regenerated via `uv export --no-hashes --no-dev` so the file matches the locked closure (138 lines, was 82).

### Notes
- The CI run takes ~3-4 minutes on a cold cache and ~90 s warm — comfortably within GitHub Actions' free-tier minutes budget for the open-source repo.
- DB-fixture tests still skip in CI for now; adding a `services: postgres:` block + setting `TEST_DATABASE_URL` is a v0.8.x patch once Neon branch-per-PR provisioning lands (separate from CI scope here).

---

## [0.8.4] — 2026-05-25

### Fixed
- **Persisted narratives were silently mislabelled.** The SSE persistence path in `app/routers/narrative.py` always wrote `provider="openai"` and `is_fallback=False`, regardless of whether the live LLM produced the text or the deterministic fallback did. In production that meant every Groq narrative was tagged "openai" and no row ever reflected a budget-exhaust or upstream-error fallback. Both columns are now derived honestly:
  - `is_fallback` is propagated through a new `NarrativeStreamMeta` dataclass that `NarrativeService.stream_narrative` writes to and the route reads after the stream finishes. Per-request state, no service-singleton race.
  - `provider` is derived from `settings.narrative_base_url` via a new `_resolve_provider` helper: `groq` for `*.groq.com`, `openrouter` for `*.openrouter.ai`, `cerebras` for `*.cerebras.ai`, `openai` for `*.openai.com` and the default, `openai-compatible` for anything else (so unknown providers are never silently mislabeled).
  - `model_name` is now `NULL` on fallback rows (matched the column's design intent — it only applies to real LLM rows).
- **Stale narrative mode CHECK constraint.** The original v0.5.0 schema allowed `mode IN ('roast','mentor','recruiter','cto','career')` but the latter three were dropped in v0.6.0 (2026-05-19). New Alembic migration `20260525_0002_trim_narrative_mode_check.py` tightens the constraint to `('roast','mentor')` and reverses cleanly via `downgrade()`. Model in `app/db/models.py` mirrors the new constraint.
- **GitHub `User-Agent` was frozen at `skill-issue/0.1.0`** (the v0.1.0 ingestion-MVP slice) despite seven minor releases shipping since. Now derived from `app.settings.VERSION` so traffic to api.github.com is attributed honestly to whatever version is actually deployed.

### Changed
- `app/narrative/service.py::stream_narrative` accepts an optional `meta: NarrativeStreamMeta` kwarg. Calls without `meta` (every existing test, every existing internal caller) work unchanged — the iterator still yields `str`, the SSE serializer stays the same.
- `app/routers/narrative.py` lifts the `from app.db.models import AnalysisRun` import out of `event_generator` into module scope.

### Tests
- 4 new unit tests in `tests/narrative/test_service.py` covering `meta.is_fallback` / `meta.fallback_reason` / `meta.cache_hit` propagation across all four paths (cache hit, budget exhaust, live stream, error fallback).
- 9 new parametrized cases in `tests/narrative/test_provider_resolution.py` covering the URL → provider mapping including the unknown-host `openai-compatible` fallback.
- Suite: 243 → 256 non-DB-fixture pass.

### Notes
- This is a hotfix that interpolates ahead of the originally-planned v0.8.4 (`revalidateTag` ISR). PLAN.md downstream shifted: `revalidateTag` → v0.8.6, `vercel.json → vercel.ts` → v0.8.7. Matches the v0.7.x and v0.8.3 hotfix precedent.
- Existing rows in `narratives` carrying the misattribution are not retroactively fixed by this release. A separate backfill (if anyone ever queries this column historically) would be SQL-only; not worth a migration since the data is dev/staging-only at this point.

---

## [0.8.3] — 2026-05-24

### Fixed
- **Analysis crashed with a generic 5xx for any GitHub profile that owned an empty repo.** Real-user report: `mohit-sharma2` (3 public repos, 2 of them `size=0`) failed analysis with a 409 surfaced through the frontend boundary. Root cause: GitHub returns `409 Conflict — "Git Repository is empty."` (not 404) on `/contents` and `/commits` endpoints when a repo has no commits yet. Our ingestion fan-out (`asyncio.gather` over all repos' commits/contents) blew up on the first 409 and never recovered.
- **Patched five `GitHubClient` methods** to treat 409 the same as the already-handled 404 — return `[]` or `None` gracefully: `list_commits`, `list_recent_commits_sample`, `get_repo_root_contents`, `list_workflow_files`, `get_repo_readme_text`. Plus `get_license` defensively, same family.

### Changed
- **`_CACHEABLE_STATUSES`** in `app/github/client.py` adds `409` so subsequent ingest calls for the same empty repo skip the GitHub round-trip. A repo doesn't become un-empty often, and even when it does, the Layer A Report cache TTL (6h) bounds staleness.
- Backend `pyproject.toml` + `app/settings.py::VERSION` + `frontend/package.json` synced at `0.8.3`. Frontend results-view footer + landing pill literals bumped.

### Notes
- This is a hotfix that interpolates ahead of the originally-planned v0.8.3 (`revalidateTag` ISR). PLAN.md downstream shifted: `revalidateTag` → v0.8.4, `vercel.json → vercel.ts` → v0.8.5. Matches the v0.7.x hotfix precedent (v0.7.3 org detection / v0.7.4 mobile badges / v0.7.5 mode toggle).
- The triggering Sentry event ID was `9925df962012425d85c6e8d99ca0448d` against `release=0.8.2` — captured by the v0.8.0 observability slice working as designed.

### Tests
- 3 new respx cases: `test_get_repo_root_contents_returns_empty_for_empty_repo_409`, `test_list_recent_commits_sample_returns_empty_on_409_empty_repo`, `test_list_commits_returns_empty_on_409_empty_repo`. The existing 404 test kept as `test_get_repo_root_contents_returns_empty_for_empty_repo_404` for defence-in-depth across GitHub API shifts.
- Suite: 240 → 243 non-DB-fixture pass.

---

## [0.8.2] — 2026-05-23

### Added
- **Manual Force-Refresh button** on every `/me` grid row. Click → `POST /me/refresh/{username}` → synchronous re-ingest via the existing `get_report_for_user` pipeline (cold call, ~5-10s) → new `analysis_runs` row → Layer A Redis cache write-through → fresh Report rendered inline. Complements v0.8.1's nightly cron for the impatient case.
- **`POST /me/refresh/{username}`** route — auth-required, ownership-strict (must be in the caller's `analyses`), rate-limited at 10 per UTC-hour per user. 429 returns `{detail: "rate_limited", retry_after_seconds: N}` + `Retry-After` header. Body returned via `JSONResponse` so FastAPI doesn't wrap it.
- **`app/cache/rate_limit.py`** — generic `try_increment_counter(cache, name, user_id, limit, hour_bucket)` returning `RateLimitResult(allowed, current, limit)`. INCR + EXPIRE-on-first-write so keys self-clean after the bucket rolls over. Reusable for v0.9.0's other limits.
- **`NAMESPACE_RATE_LIMIT`** + `rate_limit_key(name, user_id, hour_bucket)` in `app/cache/keys.py`. Keys take the shape `si:v1:rate_limit:force_refresh:<user_id>:<YYYY-MM-DD-HH>`.
- **`get_user_analysis_by_target(db, user_id, target_login)`** ownership helper in `app/persistence/analyses.py`. Case-insensitive match (mirrors v0.5.0's case-mismatch fix).
- **`<RefreshButton>`** client component — `idle → pending → success | error | rate_limited` state machine, `RefreshCw` spinner during pending, `e.preventDefault()` + `e.stopPropagation()` stop nested-Link navigation. Embedded inside the existing server-rendered `<HistoryCard>` so the row's static content stays SEO-friendly.
- **PostHog `force_refresh_clicked` event** — `target_login`, `duration_ms`, `success` properties. Fires on every settled state (success / error / rate-limited).
- **13 new tests** — 4 backend rate-limit (`tests/cache/test_rate_limit.py`), 4 backend keys (`tests/cache/test_keys_rate_limit.py`), 5 backend refresh router (`tests/routers/test_refresh.py`), 3 frontend `<RefreshButton>`, 1 events surface row. Backend suite grows 231 → 240 non-DB-fixture pass; frontend 34 → 37 vitest.

### Changed
- `Settings.force_refresh_per_user_per_hour: int = 10` — env-overridable. Default conservative enough that no production override is expected at the 100-users/day operating ceiling.
- Backend `pyproject.toml` + `app/settings.py::VERSION` + `frontend/package.json` synced at `0.8.2`. Frontend results-view footer literal `v0.8.1` → `v0.8.2`.

### Notes
- No new env vars, no new accounts. Reuses Upstash (v0.7.0), session auth (v0.5.0), `get_report_for_user` (v0.7.0), `record_run` (v0.5.0), PostHog (v0.8.0).
- The rate limit is insurance against malicious spam (a single user could otherwise burn ~3000 GH calls/min through the existing 5000/hr ceiling). At the project's 100-users/day operating ceiling, normal use never hits the cap.
- Layer A's case-insensitive `target_login` keying means user X's force-refresh of `octocat` warms the cache for user Y's saved `octocat` too — N:1 GH-call savings come for free.
- `trackForceRefreshClicked` was folded into the same commit as `<RefreshButton>` (Task 7) because the component imports it dynamically — splitting them would have left a dangling import between commits.

---

## [0.8.1] — 2026-05-22

### Added
- **Nightly cron re-ingestion** for every saved analysis. `POST /cron/refresh-saved-analyses` fires once daily at 03:00 UTC, refreshes up to 25 oldest-stale analyses per fire (cap by 24h staleness window + 240s wall-clock deadline), and write-throughs the v0.7.0 Layer A Redis cache so concurrent reads benefit. Each refresh resolves a GitHub token via the owner's most-recently-used unexpired session (decrypted from AES-GCM at-rest); falls back to `GITHUB_TOKEN` when no usable session exists.
- **`/cron/refresh-saved-analyses` bearer-authed route** in a new `app/routers/cron.py`. Constant-time bearer compare via `hmac.compare_digest`. Returns 503 when `CRON_SECRET` is unset on the backend (prod misconfig visible at first fire), 401 for missing/wrong bearer.
- **`CRON_SECRET` env var** documented in `docs/DEPLOY.md`. Vercel Cron injects `Authorization: Bearer ${CRON_SECRET}` automatically.
- **`app/cron/` package** — `RefreshOutcome` + `RefreshChunkSummary` dataclasses, `run_refresh_chunk` orchestrator with deadline guard + per-row exception isolation + rate-limit-cliff stop, `resolve_token_for_analysis` (`USER_SESSION` / `APP_FALLBACK` enum).
- **`app/persistence/refresh.py`** with `iter_stale_analyses(db, *, limit, stale_after_hours=24)` — LEFT JOIN onto `analysis_runs` via `latest_run_id`, oldest-first, `nulls_first` so analyses with no run sort before stale-but-run ones.
- **Cron event taxonomy** in `docs/OBSERVABILITY.md` — five named events (`cron.refresh_started`, `_succeeded`, `_skipped`, `_rate_limited`, `_chunk_complete`) with severity + Sentry treatment per row.
- **13 new backend tests** across `tests/cron/test_tokens.py` (4), `tests/cron/test_refresh.py` (5), `tests/cron/test_cache_writethrough.py` (1), `tests/persistence/test_refresh.py` (3), `tests/routers/test_cron.py` (4). Suite grows from 221 to 231 non-DB-fixture pass.

### Security
- **`happy-dom` `^15` → `^20`** to clear GHSA-37j7-fg3j-429f (VM Context Escape can lead to Remote Code Execution). Dev-only test environment — we never feed untrusted HTML through it, so real blast radius is nil — but AGENTS.md rule 1 ("modern tools always") + the critical severity made the bump cheap. 34/34 vitest still passes. Remaining `npm audit` is two moderate advisories inside Next 16.2.6's transitive `postcss`, cleared when Next 16.3 ships.

### Changed
- **`ruff format` pass on 51 backend files.** `ruff check` was being enforced post-v0.8.0 but `ruff format` had silently drifted across the v0.5.0 → v0.8.0 commits. Pure whitespace/style normalization, no behavior change. `docs/TECH_STACK.md` now notes that `ruff check` and `ruff format` are independent passes.
- **Backend dep refresh** (`uv lock --upgrade`, all within existing `>=` constraints): ruff 0.15.13 → 0.15.14, starlette 1.0.0 → 1.0.1, openai 2.37 → 2.38, joserfc 1.6.5 → 1.6.7, jiter 0.14 → 0.15, click 8.3.3 → 8.4.1, certifi 2026.4.22 → 2026.5.20, greenlet 3.5.0 → 3.5.1, idna 3.15 → 3.16, watchfiles 1.1.1 → 1.2.0.
- **Frontend dep refresh** (`npm update`, within `^` ranges — `package.json` unchanged): @base-ui/react 1.4.1 → 1.5.0, framer-motion 12.38 → 12.40, shadcn 4.7 → 4.8, @types/react 19.2.14 → 19.2.15. Side effect: `qs` transitive DoS advisory cleared.
- Backend `pyproject.toml` + `app/settings.py::VERSION` + `frontend/package.json` synced at `0.8.1`. Frontend results-view footer literal `v0.8.0` → `v0.8.1`.

### Notes
- `CRON_SECRET` provisioning is the gating user action — generate with `python -c "import secrets; print(secrets.token_hex(32))"` and paste into Vercel Production + Preview as Sensitive.
- Out of scope per PLAN siblings: manual "Force refresh" button (v0.8.2), `revalidateTag` for `/share/[slug]` (v0.8.3), `vercel.json → vercel.ts` (v0.8.4).
- Sentry alert rules + literal `event=cron.*` keys are deferred to a v0.8.x patch alongside the source-map upload work.

---

## [0.8.0] — 2026-05-22

### Added
- **Sentry — backend project (`skill-issue-backend`)** with FastAPI + asyncpg + httpx + logging integrations. PII scrub (`before_send`) strips `Cookie` / `Authorization` / `x-vercel-id` headers, `access_token` / `access_token_ct` / `oauth_state` / `oauth_code` / `session_id` / `email` fields from every event. Idempotent `init_sentry` guards against double-initialisation.
- **Sentry — frontend project (`skill-issue-frontend`)** via `@sentry/nextjs` 10.x. Three runtime targets covered: browser (`sentry.client.ts`), Node server-component (`sentry.server.ts`), edge (`sentry.edge.ts`). Source maps generated but upload disabled by default (`sourcemaps: { disable: true }` — lands in a v0.8.x patch when `SENTRY_AUTH_TOKEN` is provisioned). `onRequestError` Next 16 hook captures unhandled server errors. Browser + server share a single PII scrub list at `frontend/src/observability/scrub.ts`.
- **PostHog (`skill-issue`)** product analytics + real-user web vitals capture. Five named events: `analyze_submitted`, `share_toggled`, `share_card_copied`, `mode_toggled`, `sign_in_clicked`. Typed helpers in `frontend/src/observability/events.ts` are the only public contract — bare `track()` is marked `@internal`. Anonymous viewers use PostHog's auto-distinct-ID; signed-in viewers identified by the opaque `si_session` cookie value (never GitHub login or email). `<ObservabilityProvider>` wraps the layout; `<SessionIdentifier>` is Suspense-isolated for React 19 `use()` semantics.
- **Real-user web vitals** (LCP / CLS / INP / FCP / TTFB) captured by PostHog per visitor with element selectors — closes v0.7.2's open "couldn't ID the prod LCP element" gap. Free tier covers 12-month retention.
- **`structlog`** JSON renderer in prod, console in dev. Every log line carries the `request_id` from the new `RequestIDMiddleware` (UUID4, also echoed in `X-Request-ID` response header). RFC 7230 whitespace is stripped from incoming `X-Request-ID` so upstream trace chains aren't broken.
- **`RequestIDMiddleware`** — pure ASGI, binds the request_id into structlog's contextvars + Sentry's `isolation_scope` per-request. Honours an incoming `X-Request-ID` header when it's a valid UUID. Clears contextvars in a `finally` block so a mid-flight exception can't leak state.
- **`docs/OBSERVABILITY.md`** — error-budget classes (critical / acceptable / noise), alert intent, event taxonomy, cross-tool correlation guide, PII contract.
- **On-voice 404 page** (`app/not-found.tsx`) — Skill-Issue-voiced copy + CTAs to landing and the GitHub repo. Project design-system tokens (`glass`, `text-muted-foreground`, grid background) instead of generic neutrals.
- **`Sentry.captureException` hook** in `app/error.tsx` so every unhandled client error reaches Sentry with the source-mapped stack.
- **`@axe-core/cli`** dev dep. Baseline + post-fix audit captured at `docs/superpowers/measurements/2026-05-22-v0.8.0-axe-baseline.md`. **Zero critical, zero serious, zero moderate** axe issues across `/`, `/u/octocat`, `/u/octocat/card`, `/me`, `/this-does-not-exist` (the spec only required zero critical — we cleared the higher bar).

### Changed
- Backend `lifespan` now calls `init_logging()` + `init_sentry()` at startup before the DB ping.
- `RequestIDMiddleware` added to the FastAPI middleware stack — runs first on requests (outermost), so CORS rejections also get tagged with a request_id.
- `next.config.ts` left as a plain `NextConfig` export. The `withSentryConfig` wrapper was attempted but reverted in commit `3304087` post-tag — its `ignoreListedFrames` feature throws `TypeError: path argument must be of type string` when `SENTRY_ORG`/`SENTRY_PROJECT` are unset, which they will be until we provision `SENTRY_AUTH_TOKEN` for source-map upload. Runtime Sentry init lives in `instrumentation.ts` + `sentry.{client,server,edge}.ts` and is unaffected. A v0.8.x patch re-adds the wrapper once those three auth-token-related env vars are provisioned.
- `layout.tsx` wraps children in `<ObservabilityProvider>` with a Suspense-isolated `<SessionIdentifier>` so PostHog identification waits for `useSession()` to resolve without blocking child render.
- **Accessibility hardening on 4 pages**: `<div>` → `<main>` on `/u/[username]/not-found.tsx`, `/u/[username]/error.tsx`, root `/not-found.tsx`; added `sr-only` `<h1>` to `/u/[username]/loading.tsx` and `/me/loading.tsx`. Closes `landmark-one-main`, `page-has-heading-one`, and `region` axe rules. Added explicit `text-foreground` to the 404 GitHub link (was 2.38:1 contrast in headless light mode).
- Frontend version strings (`v0.7.5 → v0.8.0`) updated in the landing pill + results footer.
- Backend `pyproject.toml` + `app/settings.py::VERSION` + frontend `package.json` synced at `0.8.0`.

### Notes
- **Free-tier discipline.** Every new tool used a permanent free tier — Sentry (5K errors/mo + 50 replays/mo), PostHog (1M events/mo + 12-month retention), structlog + axe-core (OSS). No expiring trials, no 30-day-retention-only services.
- **Deferred slices.** Five originally-co-located PLAN items moved to focused v0.8.x patches: cron re-ingestion (v0.8.1), manual "Force refresh" (v0.8.2), `/share/[slug]` ISR + `revalidateTag` (v0.8.3), `vercel.json → vercel.ts` migration (v0.8.4). Sentry alert rules deferred to a v0.8.x patch once a week of baseline data is captured. CI integration of `@axe-core/cli` also deferred to a v0.8.x patch.

### Security
- Sentry's `send_default_pii` is explicitly `False` on both frontend and backend; even if a future SDK upgrade defaults this on, our `before_send` / `beforeSend` scrub will still drop the listed fields.
- The frontend PII scrub list is hoisted to a single source of truth (`frontend/src/observability/scrub.ts`) consumed by both client and server Sentry init — eliminates contract drift.
- `x-vercel-id` added to the scrub list on both frontend and backend (was missing from frontend in initial implementation, caught by code review).

---

## [0.7.5] — 2026-05-21

### Fixed
- **Roast / Mentor mode toggle was visibly asymmetric on mobile.** Container had `inline-flex` (sizes to content on desktop), but its parent in `NarrativeCard` uses `flex-col` on mobile (`align-items: stretch` by default), so the toggle stretched to fill the full row width while the two pills kept their natural `min-w-[7.5rem]` widths — leaving uneven empty space and making the active pill look disproportionately larger than the inactive one.
- **Fix:** container now uses `flex w-full sm:inline-flex sm:w-auto`, and each pill switches to `flex-1 sm:flex-none sm:min-w-[7.5rem]`. Result: on mobile the toggle fills its row and the two pills split it 50/50 (perfectly symmetric); on desktop the toggle keeps its natural compact size next to the heading. Same `layoutId` spring animation between modes; same Roast/Mentor colour treatment.

---

## [0.7.4] — 2026-05-21

### Fixed
- **Badge evidence was unreachable on mobile.** `BadgeRow` used `@base-ui/react/tooltip`, which is hover/focus-only and doesn't fire on touch — mobile users had no way to discover what a given badge meant. Switched to `@base-ui/react/popover` with `openOnHover delay={150} closeDelay={50}`, which gives every behaviour we wanted in one primitive: tap toggles on touch, hover peeks on desktop, focus + Enter/Space works for keyboard users. Cursor changed `cursor-help` → `cursor-pointer` to signal it's actually clickable. Same evidence content, same animated popup; mobile users can now read the same explanation desktop users always could.

---

## [0.7.3] — 2026-05-21

### Fixed
- **Analyzing a GitHub organization (e.g. `apache`, `microsoft`, `google`) crashed with a generic 500 + misleading "API may be down" frontend copy.** Root cause: GitHub's REST `/users/{login}` endpoint returns the same shape for users and orgs (orgs are a special account type), so our ingestion happily called the GraphQL `user(login:)` query — which returns `{"user": null}` for orgs. The downstream `pinned.get("user", {}).get("pinnedItems", {})` chain null-deref'd (the `.get("user", {})` default only fires when the *key* is absent; it returns the actual `None` when the value is null), the catch-all `except Exception` in `_live_ingest` swallowed it into a generic 500, and the frontend's `error.tsx` showed its hardcoded "API may be down" copy.
- **Detection now happens at ingestion entry.** New `NotAnIndividualError` in `app/ingestion/profile.py`, raised when `/users/{login}` returns `"type": "Organization"`. The dependency layer maps it to a 422 with detail `"'<login>' is a GitHub organization, not a user. Skill Issue scores individual developers — try a username instead."`
- **Frontend surfaces the 422 specifically.** New `<NotAnIndividual>` component (server-rendered, no JS) shows the actual detail message + Building2 icon + "Try a username" / "View on GitHub" CTAs. Routes through `page.tsx`'s typed result discriminator rather than Next's error boundary (which strips response detail in prod).
- Backend test coverage: `test_ingest_profile_rejects_organizations` (mocks `apache` org response, asserts `NotAnIndividualError` raised with the expected message shape).

### Changed
- Backend version bumped to `0.7.3` in `pyproject.toml` + `app/settings.py`.
- Frontend version strings (landing pill, results footer) bumped to `v0.7.3`.

---

## [0.7.2] — 2026-05-21

### Performance — prod-certified

Methodology corrected: measurements run directly against `https://skill-issue-tau.vercel.app/u/octocat`, 5 Lighthouse runs, median of the cold-start-filtered result. Full numbers in [`docs/superpowers/measurements/2026-05-21-v0.7.2-prod-certified.md`](./docs/superpowers/measurements/2026-05-21-v0.7.2-prod-certified.md).

| Metric | v0.7.1 prod | **v0.7.2 prod** | Budget | Pass? |
| --- | --- | --- | --- | --- |
| Performance | 90 | **94** / 100 | ≥ 95 | ⚠️ −1 (2/5 runs ≥95) |
| LCP | 2,804 ms | **2,773 ms** | ≤ 2,500 | ❌ +273 |
| TTI | 2,866 ms | **2,816 ms** | ≤ 2,500 | ❌ +316 |
| CLS | 0.080 | **0** | ≤ 0.1 | ✅ perfect |
| TBT | 228 ms | ~155 ms | — | ✅ |

**CLS structurally fixed** (both anonymous shifts eliminated). Perf score 90 → 94, TBT halved. LCP/TTI improved at the margin but remain ~10% over the strict budget — the remaining gap will be revisited with real-user metrics once v0.8.0's Sentry/PostHog land (Lighthouse-on-localhost-clicking-prod-URL has a wide noise floor; RUM is the right surface).

### Changed
- **`loading.tsx` skeleton rewritten to match `ResultsView` structure.** Lighthouse traced the 0.080 anonymous CLS to `div.min-h-screen` (the ResultsView wrapper). Root cause: skeleton had wrong section order vs the real ResultsView and was missing three components entirely (SaveShareControls, NarrativeCard, footer). When the backend `fetch` resolved, the layout reshuffled — the big-section moved from skeleton slot 2 to ResultsView slot 5, plus three new sections appeared. Skeleton now mirrors ResultsView's render order and approximate heights for every section. Skeleton → real swap is now a pure content swap with no layout shift.
- **`SiteHeader` reserves height** with `min-h-[3.75rem]` and a sized `<div className="h-9" />` Suspense fallback (was `null`). Before: header height was effectively just `py-3` padding until `useSession()` hydrated, then expanded ~36 px when the auth pill mounted — that growth pushed `div.min-h-screen` down and was the second 0.040 of the 0.080 CLS. Now the header has its hydrated height from first paint, no shift.
- **`NarrativeCard` dynamic-imported** in `results-view.tsx` (`ssr: false`). Below-the-fold component that pulls a heavy SSE-streaming client + `useSyncExternalStore` + `localStorage` subscription. CLS-safe placeholder reserves the real card's height. Initial bundle: 874 → 866 KB uncompressed (−8 KB); larger win is moving SSE client setup off the initial paint path.
- **Frontend version strings** bumped `v0.7.1 → v0.7.2` (landing pill, results footer).
- **Backend `pyproject.toml` + runtime `VERSION` constant** bumped to `0.7.2`.

### Notes
- **Methodology lesson, take two.** v0.7.1 used localhost Lighthouse and over-claimed (perf 94 locally vs 90 on prod). v0.7.2 uses prod-URL Lighthouse from the start — the honest median is 94 with substantial variance (runs span 61 to 96 perf, dominated by cold-start state). Lighthouse-on-localhost-clicking-prod has a wide noise floor; v0.8.0's RUM (Sentry/PostHog) will provide the tighter distribution needed for confident perf-budget claims.
- **Iteration cap respected.** Plan allowed up to two iterations on a stuck budget; we used both (header fix after skeleton fix; dynamic NarrativeCard after that). The third option (LCP element identification) requires PageSpeed Insights' web UI or Chrome DevTools — both deferred to v0.8.0 where they pair with the observability work.

---

## [0.7.1] — 2026-05-21

### Performance — prod-certified, partial budget pass

Re-measured against the live deploy after v0.7.1 went out. Localhost numbers (committed initially as "94/100 median") were measurement artifact — zero-network-latency localhost + simulated 4G doesn't model real WAN. Honest prod-certified numbers below; full breakdown in [final measurement report § "CORRECTION"](./docs/superpowers/measurements/2026-05-21-v0.7.1-final.md#correction-prod-certified-measurements-2026-05-21-post-deploy).

| Metric | Prod median (3 runs) | Budget | Pass? |
| --- | --- | --- | --- |
| Performance | **90** / 100 | ≥ 95 | ❌ −5 |
| LCP | **2,804 ms** | ≤ 2,500 | ❌ +304 |
| TTI | **2,866 ms** | ≤ 2,500 | ❌ +366 |
| CLS | **0.080** | ≤ 0.1 | ✅ |
| TBT | 228 ms | — | — |

v0.7.1's wins are real (the bundle changes are objectively in the build) but the budget was not fully hit. CLS passes; perf score / LCP / TTI fall ~5-15% short. Scheduled [v0.7.2](./PLAN.md) as a measurement-driven gap-closer (identify prod LCP element + the deterministic 0.080 anonymous CLS source).

- **First-load JS on `/u/[username]`:** 908 KB → **874 KB** uncompressed (−34 KB / ~10 KB gzipped). Wins split between the framer-motion `domAnimation` shrink and the @base-ui/react `optimizePackageImports` transform (150 KB chunk → 103 KB).

### Added
- **Turbopack-native bundle analyzer.** `npm run analyze` invokes `next experimental-analyze --output`; reports land under `.next/diagnostics/analyze/`. The webpack-only `@next/bundle-analyzer` does not work under Turbopack — we use the native one instead.
- **`experimental.optimizePackageImports`** in `next.config.ts` for `lucide-react` and `@base-ui/react` — tree-shakes the barrel imports the components actually use.
- **`images.remotePatterns` for `avatars.githubusercontent.com`** in `next.config.ts` — required by the avatar-image conversion below.
- **`scripts/chunk-stats.mjs`** (frontend) — small node script that reads Turbopack's `route-bundle-stats.json` and prints per-route top-N chunks with their disk sizes. Used to track bundle wins between optimizations without spelunking through the analyzer HTML by hand.
- **Per-slice measurement reports** under `docs/superpowers/measurements/` (baseline + final) capturing raw Lighthouse + bundle numbers.
- **Vitest cases** for `FramerProvider` (1) and `ShareAttribution` (2). Frontend suite is now 25/25 passing.

### Changed
- **LazyMotion features**: `domMax` → `domAnimation`. We use `m.div`/`m.circle`/`m.span` with `initial`/`animate`/`transition` only — no drag, no `AnimatePresence` shared layout, no `whileTap` springs. `domAnimation` covers the entire surface.
- **GitHub avatars** in `site-header.tsx` and `share-attribution.tsx` switched from plain `<img>` (eslint-disabled) to `next/image` with explicit width/height. Reserves layout boxes before the bytes arrive. (Note: the prod CLS=0.080 measured anonymously isn't from these avatars — anonymous viewers don't render them. The remaining shift source is open and tracked in v0.7.2.) Vercel image pipeline serves WebP/AVIF as a bonus.
- **Roast prompt rewritten for harder direct-address comedy** ([`d2a6812`](https://github.com/Shaan-alpha/Skill-Issue/commit/d2a6812)). Voice flipped from wry-observational ("the profile shows...") to second-person late-night-monologue ("you shipped X / your bio reads like Y"). Soft-profanity budget raised from 1 to 2–3 per response when they land a punchline. New "EVERYTHING ELSE IS GREEN" permission block tells the model to be confident-and-unfair on purpose. Few-shot anchors rewritten — Student (26/100) leads with the score itself and a rule-of-three on zeros; Senior (78/100, low recruiter signal) directly mocks the Dockerfile-tier bio. (Originally landed pre-v0.7.1; rolled into this release.)
- **Stale frontend version strings** updated from `v0.5.0` / `v0.4.0` to `v0.7.0`/`v0.7.1` ([`page.tsx`](frontend/src/app/page.tsx), [`results-view.tsx`](frontend/src/components/results-view.tsx)). (Pre-v0.7.1 housekeeping.)
- **Backend `pyproject.toml` version** caught up from a stale `0.4.0` to `0.7.1` — now tracks the runtime `VERSION` constant.

### Removed
- Two empty stray directories `backend/appauth/` and `backend/testsauth/` (untracked typo leftovers — never in git history). Pre-v0.7.1 housekeeping.

### Deferred
- **ISR on `/share/[slug]`** dropped from this slice. `export const revalidate = N` caches the rendered HTML, so a revoked slug would stay viewable for up to N seconds — the perf win isn't worth the revocation-correctness gap. The right answer is on-demand revalidation via `revalidateTag` from the backend's share-toggle endpoint; that lands in v0.8.0 alongside the cron + observability work that already needs a backend↔frontend invalidation channel.

### Notes
- **Measurement methodology lesson.** Initial certification was based on localhost `next start` against a warm in-process cache — that environment has zero network latency and Lighthouse's simulated 4G doesn't bridge the gap. The prod re-measurement (above) showed the local numbers were optimistic by ~800 ms on LCP. Future perf slices certify against the deploy URL or a tunnelled prod build, not localhost.
- One iteration attempted to close the gap by stripping the `m.div` opacity-fade entry animations on the aggregate-score and engineering-report panels. Reverted: cinematic animations are a non-negotiable product requirement (AGENTS.md rule 1). v0.7.2 will revisit with a smarter approach (defer below-fold work, identify the actual LCP element on prod, address the deterministic 0.080 CLS).

---

## [0.7.0] — 2026-05-20

### Added
- **Upstash Redis caching** across four fail-open layers:
  - **Layer A:** Full scored `Report` keyed by lowercased username, 6h TTL. Warm `/analyze/{user}` p95 drops from ~8s to ≤200ms.
  - **Layer B:** Singleflight `SET NX` lock around cold-cache misses — concurrent requests for the same username queue instead of fanning out parallel ingest jobs.
  - **Layer C:** Per-endpoint GitHub API response cache (profile 1h, repos 15min, languages 1h, contents 30min, commits 5min, GraphQL 15min). Stretches each user's 5000/hr GitHub rate-limit budget.
  - **Layer D:** Narrative cache + daily budget shared across Fluid Compute instances via Redis instead of per-instance `OrderedDict` / counter.
- **`GET /health` now reports `cache: up | down | unconfigured`** alongside `db` and `version`.
- **`app/cache/` module** — `RedisCache` (async fail-open JSON cache), `singleflight()` context manager, key helpers + per-endpoint TTL constants.
- **55 new backend tests** across `tests/cache/`, `tests/github/test_client_cache.py`, `tests/narrative/test_cache_redis.py`, `tests/narrative/test_budget_redis.py`, `tests/test_report_cache.py`, `tests/test_cache_integration.py`. `FakeRedis` stub with fault-injection hooks for fail-open assertions.
- **`upstash-redis` Python dep** for the REST API client (HTTP-based, Fluid-Compute-friendly).
- **Two settings fields:** `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`. Optional — when unset, every cache integration short-circuits to today's behaviour.

### Changed
- `GitHubClient.__init__` gains an optional `cache=` parameter. `_request` short-circuits GET requests through the cache when one is supplied; returns a `_CachedResponse` that mimics the `httpx.Response` surface used downstream.
- `NarrativeCache` and `DailyBudget` gain optional Redis backends behind the existing interfaces (in-process is the test-only fallback). `NarrativeService` calls the async API (`aget` / `aput` / `atry_consume`).
- `_USERNAME_RE` validation now runs *before* the cache lookup in `get_report_for_user`; the live-ingest path moves into a private `_live_ingest` helper so the cache wrap stays readable.
- Test infrastructure: `FakeRedis` + `fake_cache` fixtures lifted into top-level `backend/tests/conftest.py`. Autouse fixture clears the `@lru_cache` singletons (`get_cache`, `get_daily_budget`, `get_narrative_cache`, `get_narrative_service`) before and after each test so monkey-patched overrides actually fire.

### Notes
- No new MCP/plugin permissions required — Upstash account is user-provisioned and the two env vars are pasted into Vercel manually.
- Cron-driven background re-ingestion and the manual "Force refresh" button land in v0.8.0 alongside Sentry, so silent cron failures stay visible.
- Live `≤ 200ms p95` validation deferred to post-deploy — Upstash must be provisioned and env vars set on Vercel before warm-cache benefits show up in production.

---

## [0.6.0] — 2026-05-19

### Added
- **GitHub Receipts™.** Every analysis now produces a single canonical 1200×630 dark scorecard PNG. The card shows avatar + GitHub handle, tier name + sub-rank, the 100-point score in the tier accent colour, and the top 3 badges. Pasting an analysis URL into X, LinkedIn, Discord, or any rich-link surface shows the card inline.
- **Auto-wired OpenGraph + Twitter meta tags.** Both `/u/[username]` and `/share/[slug]` page heads now carry `og:image` and `twitter:image` tags (with `og:image:width=1200`, `og:image:height=630`, `og:image:alt`, `twitter:image:alt`, etc.) — generated by Next 16's `opengraph-image.tsx` and `twitter-image.tsx` file conventions.
- **`/u/[username]/card` preview page.** Embeds the card at correct aspect ratio with **Copy PNG** / **Download PNG** / **Copy URL** actions. Mobile-responsive at 320 / 375 / 414 / 768. Back link returns to the canonical report.
- **Inline "Share card" buttons.** Added to `save-share-controls.tsx` (signed-in viewers on `/u/[username]`) and `share-attribution.tsx` (any viewer on `/share/[slug]`).
- **First frontend test framework.** Vitest 3 + happy-dom + Testing Library + jest-dom matchers. ~20 new unit tests cover the OG palette, data fetchers, OgCard component, and CardActions interactions.
- **Bundled Inter Medium + Bold fonts** for satori (`frontend/public/fonts/`), licensed under SIL OFL 1.1 with attribution in the fonts README.

### Changed
- Narrative fallback now distinguishes daily-cap exhaustion (`[AI narrator offline — daily cap reached]`) from transient upstream errors (`[AI narrator offline — upstream hiccup]`). Quota-error responses no longer pretend the daily cap was hit. (Landed pre-v0.6.0.)
- Pruned merged-and-shipped feature branches (`feat/v0.1.0-backend-mvp`, `feat/v0.2.0-frontend-shell`, `feat/v0.3.0-identity-signals`, `feat/v0.5.0-auth-persistence`) from local + origin. `main` is the only long-lived branch going forward. (Landed pre-v0.6.0.)
- **Roadmap pivot.** Recruiter / CTO / Career narrative modes formally dropped — Roast + Mentor are the canonical two modes. Downstream slices renumber: v0.7.0 Caching, v0.8.0 Polish + Observability, v0.9.0 Beta hardening, v1.0.0 launch.

---

## [0.5.0] — 2026-05-18

### Added
- **GitHub OAuth sign-in.** Server-side OAuth flow with `read:user public_repo` scopes. Opaque server-side sessions stored in Postgres; the user's access token is encrypted at rest with AES-GCM.
- **Neon Postgres persistence.** Five tables (`users`, `sessions`, `analyses`, `analysis_runs`, `narratives`) provisioned via a single hand-authored Alembic migration. Anonymous flow unchanged.
- **Signed-in ingestion uses the user's GitHub token.** Each signed-in user gets a dedicated 5000/hr GitHub rate-limit budget instead of sharing the project's app-token quota.
- **`/me` history page.** Saved analyses listed in a sortable grid (recent / highest / lowest). Mobile responsive at 320 / 375 / 414 / 768.
- **`/share/[slug]` public read-only view.** Each saved analysis can be shared via an opt-in 12-character base64url slug (~72-bit entropy). Revoking generates a fresh slug, so old URLs stay revoked.
- **Save & Share controls** on `/u/[username]` for signed-in viewers. Anonymous viewers see no chrome change.
- **`/health` reports DB status.** Returns `{status, version, db}` so a flapping DB surfaces at the front door instead of cascading.
- **Site header** with sign-in pill / avatar menu (Base UI `Menu`), suspense-wrapped for clean SSR.
- **`NARRATIVE_BASE_URL` env var.** `NarrativeLLM` now accepts a custom OpenAI-compatible base URL so the narrative layer can run against Groq, OpenRouter, Cerebras, vLLM/Ollama, or any other OpenAI-compatible provider. Leaving the env var unset preserves the OpenAI default.
- **Vercel multi-service deployment.** Root `vercel.json` declares both `frontend` and `backend` services via `experimentalServices`. One Vercel project hosts both; the previous two-project layout retires.
- **`tools/compare_narratives.py`.** One-command local 4-way Groq model comparison (`llama-3.3-70b-versatile`, `openai/gpt-oss-120b`, `meta-llama/llama-4-maverick-17b-128e-instruct`, `moonshotai/kimi-k2-instruct-0905`) — runs ingestion + scoring through every candidate model, prints side-by-side outputs for manual quality judgement. Strips `<think>...</think>` blocks from reasoning models.

### Changed
- **Narrative provider switched to Groq + `llama-3.3-70b-versatile`** as the production default. Free tier, OpenAI-compatible, ~95% GPT-4o quality on creative writing, faster inference. OpenAI remains a drop-in alternative — only `NARRATIVE_BASE_URL` (Groq endpoint) and `NARRATIVE_MODEL` (Groq model id) change in env vars.
- **Sharpened roast & mentor system prompts.** Word target trimmed (roast 120-200, mentor 140-220) so outputs don't ramble; explicit failure-modes lists ("if it could appear on a LinkedIn endorsement, delete it"; banned vocabulary "keep grinding"/"you got this"/"exciting journey"/...); soft profanity allowed in roast for emphasis (`shit`, `crap`, `bullshit`, `hell`, `goddamn`, `holy hell`, `jesus`) with hard limits (no slurs, no -isms, no violent language, never insult the human's intelligence or worth); per-mode temperature (roast 0.95, mentor 0.55); evidence-rich payload now passes the full per-bucket `{points, max_points, evidence[]}` so the model can cite specific signals; tier ladder anchored in both system prompts to prevent invented tier names ("Senior Builder" hallucination); few-shot examples upgraded from ~50-word terse anchors to ~250-word evidence-dense anchors.
- `NarrativeCard` uses `useSyncExternalStore` against `localStorage` instead of `useEffect` setState — eliminates React 19's `react-hooks/set-state-in-effect` warning and adds free cross-tab sync. (Pre-v0.5.0 audit.)
- FastAPI route handlers (`/analyze`, `/narrative`) use the modern `Annotated[T, Depends(...)]` pattern. (Pre-v0.5.0 audit.)
- `react` / `react-dom` bumped `19.2.4` → `19.2.6` (patch). (Pre-v0.5.0 audit.)
- CORS middleware now allows `POST`, `DELETE`, and credentials so cookies round-trip from the frontend.

### Fixed
- **Neon Postgres URL scheme normalization.** Vercel's Neon integration emits `postgresql://...?sslmode=require&channel_binding=require` — SQLAlchemy without an explicit dialect tried to load `psycopg2` (not installed) and the function crashed at module load. `app.db.engine._normalize_async_url` now coerces any of `postgres://`, `postgresql://`, `postgresql+psycopg2://`, or `postgresql+psycopg://` to `postgresql+asyncpg://`, strips libpq-only query params asyncpg doesn't understand (`sslmode`, `channel_binding`, `gssencmode`, `target_session_attrs`, etc.), and opts into TLS via asyncpg's own `ssl=True` connect arg when the original URL signalled it.
- **OAuth state cookie path.** Previously set to `/auth`, which didn't match the Vercel multi-service callback URL `/_/backend/auth/callback`; the browser dropped the cookie and every callback hit returned `{"error":"invalid_state"}`. Cookie path is now `/` — matches everywhere, kept short-lived (10-min TTL) anyway so the broader scope is fine.
- **Share URL pointed at backend JSON, not frontend page.** `_public_share_url` derived its base from `OAUTH_REDIRECT_URL`, which on multi-service deploys includes the `/_/backend` service prefix. Switched to the first origin in `CORS_ALLOW_ORIGINS` — the frontend's canonical origin. Share URL is now `https://<host>/share/<slug>` (Next.js page) instead of `https://<host>/_/backend/share/<slug>` (raw JSON).
- **Save/Share controls rendered disabled** for signed-in viewers because `/u/[username]/page.tsx` looked up the analysis row by URL slug case (e.g. `shaan-alpha`) while the backend stored `target_login` as GitHub's canonical case (`Shaan-alpha`). No match → `analysisId = null` → button disabled. Now passes `report.username` (canonical case from the backend response) into the hint lookup AND compares case-insensitively as defence in depth.
- Cleared all 16 outstanding backend ruff warnings without regressing tests. (Pre-v0.5.0 audit.)

### Security
- GitHub access tokens never stored in plaintext. AES-GCM encryption at rest with a per-environment `SESSION_TOKEN_ENC_KEY`.
- OAuth state token bound to a short-lived `httpOnly` cookie + constant-time compare against the query param (CSRF defence per RFC 6749 §10.12).
- Share slug enumeration mitigated by 72-bit `secrets.token_urlsafe` entropy and identical 404 response for missing-vs-revoked slugs.
- `/auth/callback` never honours a `redirect_to` parameter — hard-coded `302 /` closes off open-redirect phishing.

---

## [0.4.0] — 2026-05-16

### Added
- **AI Narrative Layer** with real-time streaming Roast Mode and Mentor Mode breakdowns wrapping every engineering report.
- **SSE Streaming API (`/narrative/{username}`)** delivering prompt-injection-hardened, on-voice AI commentary token by token with zero perceived latency.
- **In-process LRU Caching** ensuring instant repeat visits and seamless mode toggling.
- **Daily Budget & Fallback Engine** protecting OpenAI quotas while maintaining a 100% resilient UI via high-quality deterministic fallback copy when offline.
- **Cinematic UI Controls** featuring a smooth `layoutId`-animated Mode Pill Toggle, live typing cursor indicator, and ambient glow effects matching the Apple HIG / Linear aesthetic standard.

---

## [0.3.0] — 2026-05-16

### Added
- **7-tier ladder** replacing the old multi-axis category model: Hobbyist · Student Builder · Entry-Level Engineer · Professional Developer · Senior Engineer · Staff Engineer · Principal Engineer. Band semantics `[lower, upper)` except Principal which includes 100.
- **Intra-tier sub-rank (1–100)** rendered alongside the tier name (e.g. "Senior Engineer · 47/100").
- **Position bar** on the results page: minimal-marker style with tier dividers, "X pts to <next tier>" caption, `role="progressbar"` semantics, lazy-loaded framer-motion animation.
- **Eight stackable badges**, all deterministic: OSS Contributor, PR Master, Maintainer, Star Magnet, Polyglot, Long-haul, Indie Hacker, Toolmaker. Each ships with a one-line evidence string.
- **Tier-gated depth signals**:
  - Professional+: per-repo license (SPDX-validated), workflow file counts, README length.
  - Senior+: PR review depth (avg body length across last 25 reviews), dependency file detection.
  - Staff+: commit message quality sampling, cross-repo contribution count.
- Two-pass scoring engine: base file-existence scoring → tier-gated enrichment → re-score on enriched profile.

### Fixed
- **`repo_quality.license_majority` (4 pts).** Deferred since v0.1.0. Finally fires when ≥50% of the top 10 non-fork repos carry an SPDX-recognised license. Makes the 100/100 ceiling reachable for the first time.

### Changed
- **Breaking — `/analyze/{username}` response shape.** `report.category: DeveloperCategory` removed; replaced with `report.tier: TierInfo` and `report.badges: list[Badge]`. Frontend types updated in lockstep. No live persistence exists yet, so no migration story is needed.

---

## [0.2.0] — 2026-05-15

### Added
- Next.js 16 + React 19 + Tailwind 4 frontend with landing page (`/`) and results route (`/u/[username]`). Mobile-first responsive across all breakpoints.
- `LazyMotion` (`framer-motion`) wired through a `FramerProvider` so animation features are lazy-loaded — smaller initial JS bundle.
- Loading skeleton mirroring the results layout (no layout jump between loading and loaded states).
- Segment-level `not-found.tsx` (on-voice "no such GitHub user") and `error.tsx` (retry + home, with optional digest reference) boundaries for `/u/[username]`.
- Search bar that accepts `github.com/<user>` URLs, `@user` shorthand, and validates the username pattern client-side before navigating.
- Backend `/analyze/{username}` GitHub-username validator — invalid input returns a clean 400 instead of a stack trace.
- Backend CORS middleware. Allowed origins configurable via `CORS_ALLOW_ORIGINS`; preview-deploy URLs supported via `CORS_ALLOW_ORIGIN_REGEX`.
- End-to-end integration test (`tests/test_analyze_e2e.py`) covering happy-path, 404 (unknown user), 400 (invalid username across 8 shapes), and 500 (missing token).
- Per-repo signal detection: ingestion now fetches each repo's root contents and populates `has_readme`, `has_tests`, `has_ci`, and `deployment_hints` (Dockerfile, vercel.json, fly.toml, netlify.toml, render.yaml, serverless, Heroku, Cloudflare, etc.).

### Fixed
- `/analyze` no longer wraps every exception as a 404. Real "not found" returns 404, GitHub HTTP errors return 502, anything else returns 500 with the full traceback logged.
- `consistency.score` previously crashed on `strptime(datetime, ...)` and `learning_trajectory.score` crashed comparing naive vs aware datetimes. Root cause: ingestion produced `YYYY-MM-DD` strings that Pydantic coerced into naive datetimes. Ingestion now writes tz-aware UTC datetimes directly.
- **Scoring engine signals now actually fire.** `_repo_from_rest` previously hardcoded `has_readme`, `has_tests`, and `has_ci` to `False` and only ever appended `"pinned"` to `deployment_hints`. ~28 of 100 scoring points were unreachable in production. Fixed by enriching the top 20 non-fork repos with their root-tree contents.
- A11y: minimum readable font size raised to `12px` (`text-xs`) for badges, the analysis ID line, the metadata grid, the error-digest line, and the footer.
- A11y: `aria-hidden="true"` on decorative icons in `SearchBar`, `ResultsView`, `not-found.tsx`, and `error.tsx`; `aria-label` on the external profile link.
- A11y: `ResultsView` semantic heading structure cleaned up — single `<main>` with a screen-reader-only `<h1>`, `<h2>` for sections.
- Performance: tightened animation timings in `ResultsView` so the aggregate score paints faster (LCP target < 2.5s).

### Changed
- `Report` JSON shape exposed to the frontend now uses `breakdown.<bucket>.points / max_points` — the previous draft type (`total_score`, `score`, `max_score`, untyped `evidence`) was wrong and would have crashed the UI.

---

## [0.1.0] — 2026-05-15

### Added
- Backend MVP skeleton using FastAPI, Pydantic v2, and `uv`.
- Async GitHub client with REST/GraphQL support and robust rate-limit handling.
- Deterministic scoring engine with scorers for `repo_quality` (30 pts), `engineering_maturity` (20 pts), `oss_collab` (15 pts), `consistency` (10 pts), `recruiter_signal` (15 pts), and `learning_trajectory` (10 pts).
- Ingestion layer for GitHub profiles, pinned repositories, language statistics, external PR/review activity, multi-repo commit patterns, and professional verification markers.
- REST API endpoint `/analyze/{username}` for end-to-end ingestion and scoring.
- Scoring engine orchestrator that aggregates 6 category scorers into a final weighted scorecard with automated developer categorization (e.g., Senior Engineer, OSS Contributor).
- Unit testing suite with fixture profiles for every scorer and integration tests for the scoring engine.


---

## [0.0.1] — 2026-05-15

### Added
- Automated GitHub Release pipeline at [`.github/workflows/release.yml`](./.github/workflows/release.yml). Pushing a `vX.Y.Z` tag now extracts the matching CHANGELOG section and publishes it as a GitHub Release. Prerelease tags (e.g. `v0.1.0-rc.1`) are flagged as prereleases automatically.

### Changed
- [`AGENTS.md`](./AGENTS.md) rule 3 extended: every version bump — minor and patch alike — must ship as a GitHub Release. There are no internal-only version bumps. Changelog entries are now written as public release notes, not internal logs.

### Notes
- This is the first patch release. It exists to install the release pipeline itself, so future version bumps automatically produce public releases.

---

## [0.0.0] — 2026-05-15

### Added
- Initial repository scaffolding.
- `README.md` — project intro and documentation index.
- `AGENTS.md` — the five rules of engagement for every agent and contributor.
- `CLAUDE.md` — Claude-specific pointer to `AGENTS.md`.
- `PLAN.md` — full versioned roadmap from v0.0.0 → v1.0.0.
- `CHANGELOG.md` — this file.
- `ARCHITECTURE.md` — system design and MCP ecosystem.
- `docs/PRODUCT_VISION.md` — personality, scoring rubric, voice.
- `docs/TECH_STACK.md` — every dependency and why.
- `docs/PROGRESS_LOG.md` — running narrative log.
- `.gitignore` — Node, Python, env, and OS noise.
- Persistent agent memory entries under `~/.claude/projects/.../memory/` for the five durable rules and the project profile.

### Decided
- **Backend host: Vercel Functions (Fluid Compute).** Single dashboard with the frontend, OIDC env handoff, native marketplace integration with Neon + Upstash. Long re-ingestion (v0.7.0+) will be chunked via Vercel Cron.

### Notes
- No application code yet. Repository contains only documentation, license, and configuration.
- All future work proceeds version-by-version per `PLAN.md`.

---

<!--
Template for new releases:

## [X.Y.Z] — YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...

### Removed
- ...

### Security
- ...
-->
