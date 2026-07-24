# Skill Issue — Implementation Plan

> **Audience:** Any agent (Claude, Gemini, Cursor, human) picking up the project cold. Read [`AGENTS.md`](./AGENTS.md) first, then this file, then [`docs/PROGRESS_LOG.md`](./docs/PROGRESS_LOG.md) for what was last touched.

**Goal:** Ship a public, viral GitHub intelligence platform that produces honest, deterministic, explainable engineering reports from a GitHub username.

**Architecture (one paragraph):** A Next.js 16 App Router frontend (Tailwind v4 + shadcn/ui + Framer Motion + Base UI primitives) talks to a FastAPI backend running on **Vercel Functions (Fluid Compute)** — locked 2026-05-15. The backend ingests a GitHub profile via the GitHub REST + GraphQL APIs, runs a deterministic two-pass scoring engine (base scoring → tier-gated depth enrichment → re-score), and then asks an LLM (OpenAI) to format the result as narrative — never to do the technical analysis itself. State persists in Neon Postgres; hot caches sit in Upstash Redis. Auth is GitHub OAuth. Long re-ingestion runs are chunked via Vercel Cron in v0.8.0 to stay within function duration caps.

**Tech stack:** See [`docs/TECH_STACK.md`](./docs/TECH_STACK.md). System diagram in [`ARCHITECTURE.md`](./ARCHITECTURE.md). Product personality in [`docs/PRODUCT_VISION.md`](./docs/PRODUCT_VISION.md).

**Versioning rule:** Work proceeds in semver-style slices. Each `v0.X.0` is a shippable milestone with explicit **exit criteria**. Do not start `v0.(X+1).0` until `v0.X.0` exit criteria are met *and* recorded in [`CHANGELOG.md`](./CHANGELOG.md).

---

## Version map (at a glance)

| Version | Slice | Status |
| --- | --- | --- |
| **v0.0.0** | Repo + docs scaffolding | ✅ shipped |
| **v0.0.1** | Automated GitHub Release pipeline | ✅ shipped |
| **v0.1.0** | Backend MVP — GitHub ingestion + deterministic scoring | ✅ shipped |
| **v0.2.0** | Frontend shell — landing page + analyze flow + results page (static) | ✅ shipped |
| **v0.3.0** | Identity Signals — 7-tier ladder, position bar, badges, tier-gated depth | ✅ shipped |
| **v0.4.0** | AI narrative layer — Roast Mode + Mentor Mode | ✅ shipped |
| **v0.5.0** | Auth + persistence — GitHub OAuth + Neon Postgres | ✅ shipped |
| **v0.6.0** | GitHub Receipts™ — shareable OG cards (dark canonical) | ✅ shipped |
| **v0.7.0** | Caching (backend) — Upstash Redis, singleflight, GitHub-API + Report + narrative caches | ✅ shipped |
| **v0.7.1** | Performance (frontend) — Lighthouse ≥ 95, TTI ≤ 2.5s, LCP ≤ 2.5s, CLS ≤ 0.1 | ⚠️ shipped, partial budget pass (prod perf 90/95, LCP 2,804/2,500) |
| **v0.7.2** | Perf gap-closer — CLS structural fix + dynamic NarrativeCard | ⚠️ shipped, CLS perfect, perf 94/95 (1 short at noise floor) |
| **v0.7.3** | Hotfix — detect GitHub organizations + helpful 422 (was: silent 500 on `apache`, `microsoft`, etc.) | ✅ shipped |
| **v0.7.4** | Hotfix — badge evidence reachable on mobile (Tooltip → Popover with hover + tap) | ✅ shipped |
| **v0.7.5** | Hotfix — Roast/Mentor toggle symmetric on mobile (flex-1 split 50/50) | ✅ shipped |
| **v0.8.0** | Polish + observability — Sentry (FE+BE), PostHog (events + web-vitals), structured logging, axe a11y pass, on-voice 404/500, error-budget doc | ✅ shipped |
| **v0.8.1** | Cron daily re-ingestion of saved analyses (paired with Sentry so failures aren't silent) | ✅ shipped |
| **v0.8.2** | Manual "Force refresh" on `/me` + `POST /me/refresh/{username}` (synchronous re-ingest, 10/hr per-user cap) | ✅ shipped |
| **v0.8.3** | Hotfix — empty-repo 409 from GitHub `/commits` and `/contents` no longer crashes analysis | ✅ shipped |
| **v0.8.4** | Hotfix — narrative persistence honesty (`is_fallback` + `provider` derived correctly, narrative-mode CHECK trimmed, GH `User-Agent` tracks VERSION) | ✅ shipped |
| **v0.8.5** | CI pipeline (`pytest` + `ruff` + `npm lint/test/build` on every PR) + `requirements.txt` regenerated (was missing 9 of 15 direct deps) | ✅ shipped |
| **v0.8.6** | On-demand `revalidateTag` for `/share/[slug]` ISR (closes v0.7.1's deferred share-page caching) | ✅ shipped |
| **v0.8.7** | `vercel.json` → `vercel.ts` migration (Vercel 2026-02-27 knowledge update) | ✅ shipped |
| **v0.9.0** | Bounded GH fan-out (asyncio.Semaphore around ingest_profile gathers) | ✅ shipped |
| **v0.9.1** | `/me/analyses` N+1 fix + Layer A cache schema version | ✅ shipped |
| **v0.9.2** | Rate limiting (IP + user) on `/analyze` + `/narrative` | ✅ shipped |
| **v0.9.3** | Deletable `/me` history + back-nav loading fix + creator flair | ✅ shipped |
| **v0.9.4** | DB pool size env-tunable + real back-nav spinner fix | ✅ shipped |
| **v0.9.5** | Security review + hardening (OAuth scope ↓ `read:user`, HTTP security headers) | ✅ shipped |
| **v0.9.6** | Load-test harness (warm /analyze; full 100 RPS run = operator step) | ✅ shipped |
| **v0.9.7** | Privacy policy + terms + global footer | ✅ shipped |
| **v0.9.8** | Launch landing sections (examples + how-it-works + star CTA) | ✅ shipped |
| **v1.0.0** | First stable release (launch polish) — public-launch ops in docs/LAUNCH.md | ✅ shipped |
| **v1.0.1** | Launch Ops — GitHub Education perks + domain cutover (docs/LAUNCH.md) | ✅ shipped |
| **v1.0.2** | Security & hardening — 2026-07-13 audit remediation (headers, dep CVEs) | ✅ shipped |
| **v1.0.3** | Hotfix — `/analyze` survives GitHub GraphQL resource limits | ✅ shipped |
| **v1.0.4** | Cost-control fairness & hardening — 2026-07-24 audit (per-subject LLM budget, fail-closed limits, spoof-proof IP, Sentry scrub, CI perms) | ✅ shipped |
| **v1.0.5** | Ingest amplification containment (cores) — call cap, Retry-After/deadline, budget refund on abort, OG attribution, holder-checked lock | ✅ shipped |
| **v1.0.6** | Shared-token quota breaker (SI-03 ext) — sheds new anon analyses before the shared GitHub token is exhausted. SSE coalescing dropped; OG store-gating deferred | ✅ shipped |

---

## v0.0.0 — Scaffolding ✅

**Goal:** A cold agent can read the repo and understand the project, the rules, and what to build next.

**Exit criteria:**
- [x] `README.md`, `AGENTS.md`, `CLAUDE.md`, `PLAN.md`, `CHANGELOG.md`, `ARCHITECTURE.md` exist at repo root
- [x] `docs/PRODUCT_VISION.md`, `docs/TECH_STACK.md`, `docs/PROGRESS_LOG.md` exist
- [x] `.gitignore` covers Node, Python, env files, OS noise
- [x] Memory (`~/.claude/.../memory/`) populated with project + feedback entries

---

## v0.1.0 — Backend MVP: ingestion + deterministic scoring

**Goal:** Given a GitHub username, the backend returns a JSON report with the developer category and the six-bucket 100-point score. No AI involved yet. No frontend yet.

**Why this first:** The product's defensible value is the scoring engine. The AI layer is decoration. Build the spine first.

**Slice scope:**
- FastAPI project skeleton under `backend/`
- GitHub client (`httpx`, async) with REST + GraphQL coverage, token via env, polite rate-limit handling
- Ingestion layer that pulls: profile, pinned repos, top N repos, recent commits, PRs opened/reviewed, issues, language breakdown, contribution graph
- Six deterministic scorers (one module each):
  - `repo_quality.py` (30 pts) — README presence/length, tests directory, CI config, deployment hints (Dockerfile, vercel.json, etc.), license, recent commits
  - `engineering_maturity.py` (20 pts) — folder structure heuristics, module count vs. file count, dependency hygiene, branching activity
  - `oss_collab.py` (15 pts) — external PRs, reviews, cross-org activity
  - `consistency.py` (10 pts) — commit cadence variance, longest dry spell, recency
  - `recruiter_signal.py` (15 pts) — profile README, bio, stack relevance, pinned curation
  - `learning_trajectory.py` (10 pts) — repo-creation-date complexity trend, stack diversification over time
- `category.py` — rule-based developer category classifier driven by score profile + activity shape
- `/analyze/{username}` endpoint returning the full structured report
- Unit tests for every scorer with fixture profiles (`tests/fixtures/`)
- One end-to-end integration test against a real public profile (rate-limit-aware)

**Exit criteria:**
- [x] `cd backend && uv run uvicorn app.main:app --reload` boots the API
- [x] `GET /analyze/octocat` returns a complete, well-typed JSON report in under 10s (warm)
- [x] All scorers have ≥ 3 fixture-driven unit tests with explicit expected numbers
- [x] Total score is the literal sum of the six buckets — no fudge factors
- [x] `CHANGELOG.md` and `docs/PROGRESS_LOG.md` updated; version bumped to `0.1.0`

**Sub-plan:** When this slice starts, generate a detailed TDD plan via the `superpowers:writing-plans` skill and save to `docs/superpowers/plans/YYYY-MM-DD-v0.1.0-backend-mvp.md`.

---

## v0.2.0 — Frontend shell

**Goal:** Public-facing Next.js app with a landing page, an analyze flow, and a results page that consumes the v0.1.0 backend. Static report rendering only — no AI narrative yet, no auth.

**Slice scope:**
- `frontend/` Next.js 16 App Router project, TypeScript, Tailwind v4, shadcn/ui, Base UI, Framer Motion
- Landing page matching `docs/PRODUCT_VISION.md` voice: hero, subtext, one CTA (`Analyze My GitHub`)
- `/u/[username]` route that calls the backend and renders the report
- Six score cards, animated entry, with deterministic narrative placeholders (e.g. "AI take coming in v0.3")
- Developer category badge
- Loading and error states
- Lighthouse mobile score ≥ 90 on the results page

**Exit criteria:**
- [x] Deployed preview URL on Vercel renders `/u/octocat` end-to-end against the backend
- [x] Visual review: zero crypto-dashboard / neon-gradient violations of `docs/PRODUCT_VISION.md`
- [x] Lighthouse performance ≥ 90 and Accessibility ≥ 95 on results page
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.2.0`

---

## v0.3.0 — Identity Signals

**Goal:** Replace the bare score number with a tier ladder, intra-tier sub-rank, position bar, and stackable badges. Aggressive tier-gated depth signals unlock richer evidence at higher tiers and finally fire the deferred 4-pt license signal at Professional+.

**Design spec:** [`docs/superpowers/specs/2026-05-16-v0.3.0-identity-signals-design.md`](./docs/superpowers/specs/2026-05-16-v0.3.0-identity-signals-design.md).

**Slice scope:**
- Backend: new `scoring/category.py` (7-tier ladder + sub-rank math), `scoring/badges.py` (8 deterministic v1 badges), `scoring/depth.py` (tier-gated enrichment dispatcher).
- Ingestion: license / CI workflow / README-quality calls at Professional+; PR review depth + dependency hygiene at Senior+; commit message quality + cross-repo refactor signal at Staff+.
- Model: drop `Report.category: DeveloperCategory`; add `Report.tier: TierInfo` and `Report.badges: list[Badge]`. New `TierName` literal.
- Frontend: new `position-bar.tsx` (`role="progressbar"`, minimal-marker style) and `badge-row.tsx` on the results page; loader skeleton updated to match.
- Tests: per-tier boundary cases, per-badge under/at/over fixtures, depth-signal mocks, e2e shape update.

**Exit criteria:**
- [x] `/analyze/{username}` returns `tier` and `badges` in the new shape for every fixture and real-user request.
- [x] All 7 tier names assignable from crafted fixtures; band semantics `[lower, upper)` with Principal `[90, 100]`.
- [x] Every v1 badge has ≥ 3 unit-test cases (under / at / over).
- [x] The licence signal earns its 4 pts on at least one Professional+ fixture — torvalds reaches 65/100 (Senior Engineer) with the +4 from `license_majority`; Shaan-alpha reaches 30/30 on `repo_quality`. 100/100 ceiling now provably reachable.
- [x] Position bar renders correctly in the browser for octocat (Student Builder · 80% into tier) and torvalds (Senior Engineer · just promoted).
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.3.0`.

**Sub-plan:** [`docs/superpowers/plans/2026-05-16-v0.3.0-identity-signals.md`](./docs/superpowers/plans/2026-05-16-v0.3.0-identity-signals.md) — 22 tasks, all completed. Lighthouse re-measurement deferred to v0.9.0 (Polish + observability) where it becomes an explicit exit criterion across the whole results route.

---

## v0.4.0 — AI narrative layer

**Goal:** Roast Mode and Mentor Mode produce streaming, on-voice narrative wrapping every Report. The LLM never alters scores; it only formats them.

**Design spec:** [`docs/superpowers/specs/2026-05-16-v0.4.0-narrative-design.md`](./docs/superpowers/specs/2026-05-16-v0.4.0-narrative-design.md).

**Sub-plan:** [`docs/superpowers/plans/2026-05-16-v0.4.0-narrative.md`](./docs/superpowers/plans/2026-05-16-v0.4.0-narrative.md) — 18 TDD tasks, ready for execution.

**Slice scope:**
- Backend `app/narrative/` with six small focused modules (`cache`, `budget`, `prompts`, `fallback`, `llm`, `service`). Single OpenAI boundary in `llm.py`; tests use `FakeNarrativeLLM` and never hit the network.
- New `GET /narrative/{username}?mode={roast|mentor}` SSE endpoint streaming token-by-token via `text/event-stream`.
- In-process LRU cache (256 entries) keyed by `(username, scores_hash, mode)`. UTC-rolling daily budget (`NARRATIVE_DAILY_LIMIT`, default 50) with a deterministic on-voice fallback narrative when exhausted — page never goes blank.
- Strict prompt contract: full Report passed as JSON in the `user` message (not interpolated); system prompt instructs the model to treat the JSON as data. Two layers against prompt injection (regex on username + JSON envelope).
- Few-shot calibration set drawn from `docs/PRODUCT_VISION.md` voice anchors.
- Frontend: replace v0.3.0's right-hand "Engineering Report" hero card with `NarrativeCard` — pill toggle (Roast / Mentor) + streaming text with typing cursor + fallback toast. Mode preference persists in `localStorage`.
- Prompt regression suite: 5 fixture profiles × 2 modes = 10 committed snapshots of the assembled `messages` array.

**Exit criteria:**
- [x] `/narrative/{username}?mode=roast` streams a valid SSE response for all 5 fixture profiles (Hobbyist → Staff).
- [x] `mode=mentor` produces tonally distinct output from `mode=roast` for the same profile (snapshot diff asserts the prompt diverges; live smoke confirms the output diverges).
- [x] Toggling modes on `/u/{username}` never changes the displayed score, tier, badges, or position bar.
- [x] `NARRATIVE_DAILY_LIMIT=0` makes every request hit the fallback path; UI shows the offline badge; rest of the page unaffected.
- [x] No prompt-injection succeeds for adversarial usernames or report fields (regex + JSON envelope verified by tests).
- [x] Second call with same `(username, scores_hash, mode)` returns in < 200ms, no LLM call (LRU cache hit).
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.4.0`.

---

## v0.5.0 — Auth + persistence

**Goal:** Users sign in with GitHub. Analyses are stored. Repeat visits are fast. Signed-in users get a dedicated 5000/hr GitHub rate-limit budget by using their own access token during ingestion.

**Design spec:** [`docs/superpowers/specs/2026-05-16-v0.5.0-auth-persistence-design.md`](./docs/superpowers/specs/2026-05-16-v0.5.0-auth-persistence-design.md).

**Slice scope:**
- GitHub **OAuth App** (not GitHub App), server-side flow, scope `read:user` (v0.9.5 dropped `public_repo`). State token in a short-lived httpOnly cookie. Server-side opaque sessions in Postgres (no JWT).
- **Neon Postgres** schema (5 tables): `users`, `sessions`, `analyses`, `analysis_runs`, `narratives`. Cascade deletes from `users` clean everything up.
- **SQLAlchemy 2.0 async + asyncpg** against Neon's pooled host (port 6543, `statement_cache_size=0`). Direct host (port 5432) only for Alembic migrations.
- **Alembic** migrations, hand-edited, reversibility tested.
- GitHub access tokens **encrypted at rest** with AES-GCM (key from `SESSION_TOKEN_ENC_KEY`); never plaintext in the DB.
- New routes: `/auth/{login,callback,logout}`, `/me`, `/me/analyses`, `POST|DELETE /analyses/{id}/share`, `GET /share/{slug}`. Existing `/analyze` and `/narrative` gain optional persistence when a session is present — anonymous flow unchanged.
- Frontend: site header with GitHub sign-in / avatar menu, `/me` history grid, `/share/[slug]` read-only public view, Save + Share affordances on `/u/[username]` for signed-in viewers. Mobile responsive at 320 / 375 / 414 / 768.
- Analyses are private by default; sharing is opt-in and generates a 12-char base64url (~72-bit) slug. Revoking nulls both `is_public` and `share_slug`.

**Exit criteria:**
- [x] `uv run alembic upgrade head` creates all 5 tables on a fresh Neon branch; `alembic downgrade base` drops them.
- [x] Sign-in flow works in preview and prod (verified manually in both). Live at https://skill-issue-tau.vercel.app.
- [x] Signed-in `/analyze/{user}` persists `analyses` + `analysis_runs`; anonymous calls write nothing.
- [x] Signed-in `/narrative/{user}` persists a `narratives` row on success; anonymous calls write nothing.
- [x] `GET /me/analyses` returns 20-per-page history sorted by latest run; `sort=score_desc|score_asc|recent` works.
- [x] Share toggle round-trip: `POST /analyses/{id}/share` returns slug, `GET /share/{slug}` returns the analysis, `DELETE /analyses/{id}/share` → 404 on the slug.
- [x] `SELECT access_token_ct FROM sessions LIMIT 1` returns binary BYTEA — no raw GitHub tokens in the DB.
- [x] `uv run pytest -q` passes with 62 new tests across auth, db, persistence, routers, and integration paths (186 total, up from 124).
- [x] `npm run lint && npm run build` clean.
- [x] Mobile browser smoke (320 / 375 / 414 / 768): sign in → save → share → open share URL in incognito → sign out.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.5.0`.

**Sub-plan:** When this slice starts, generate a detailed TDD plan via the `superpowers:writing-plans` skill and save to `docs/superpowers/plans/2026-05-16-v0.5.0-auth-persistence.md`.

---

## v0.6.0 — GitHub Receipts™

**Goal:** Every analysis produces a single canonical, shareable scorecard image suitable for LinkedIn, X, and OG previews. Roast + Mentor remain the only narrative modes — no Recruiter / CTO / Career (deferred to "Beyond v1.0" ideas).

**Design spec:** [`docs/superpowers/specs/2026-05-19-v0.6.0-receipts-design.md`](./docs/superpowers/specs/2026-05-19-v0.6.0-receipts-design.md).

**Slice scope:**
- Next.js `@vercel/og` route at `/u/[username]/og.png` (private analyses → 404 unless owner) and `/share/[slug]/og.png` (public, no auth) generating a 1200×630 PNG via `next/og`'s `ImageResponse` (satori, no headless browser).
- One canonical dark card variant: avatar + GitHub handle, tier name + sub-rank, large 100-pt total, top 3 badges, brand mark, subtle background. No gradient soup, no neon, no narrative text on the card itself (deterministic content only → render is run-stable).
- Dedicated preview route `/u/[username]/card` with: card preview at correct aspect ratio, "Copy PNG", "Download PNG", "Copy share URL" actions, and the OG meta tags (Twitter/X `summary_large_image`, OpenGraph) wired so the route itself has rich previews.
- Inline "Share card" affordance added to `save-share-controls.tsx` on `/u/[username]` (signed-in) and `share-attribution.tsx` on `/share/[slug]` (public) — opens the new `/u/[username]/card` page in-context.
- OG meta tags injected into `/u/[username]` and `/share/[slug]` page heads so the PNG renders inline when the analysis URL is pasted into X, LinkedIn, Discord, etc.

**Out of scope:** light variant, "full breakdown" variant, multi-platform analytics, headless-browser fallback. All deferred to a future v0.6.x patch if real demand surfaces.

**Exit criteria:**
- [x] `GET /u/{username}/opengraph-image` returns a valid 1200×630 PNG (and the matching `/twitter-image` route). Live verification of the p95 ≤ 800ms target deferred to post-deploy; Vercel edge cache + Fluid Compute will dominate the typical path.
- [x] `GET /share/{slug}/opengraph-image` returns the same card for the shared analysis with no auth, including a clean fallback PNG on unknown slugs.
- [x] `/u/{username}/card` renders the preview + 3 actions (Copy PNG, Download PNG, Copy URL) and looks correct at 320 / 375 / 414 / 768 / desktop widths.
- [ ] Pasting `https://skill-issue-tau.vercel.app/share/<slug>` into X and LinkedIn shows the card inline — verified post-deploy.
- [x] Card render is deterministic for a given report — three local renders returned byte-identical 63171-byte PNGs.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.6.0`.

---

## v0.7.0 — Caching + performance (backend)

**Goal:** Repeat analyses are free and fast. A warm `/analyze/{user}` drops from ~8s to ≤200ms p95.

**Design spec:** [`docs/superpowers/specs/2026-05-19-v0.7.0-caching-design.md`](./docs/superpowers/specs/2026-05-19-v0.7.0-caching-design.md).

**Slice scope:**
- **Upstash Redis** (user-provisioned account, env vars pasted into Vercel manually — no Marketplace integration). REST API via the `upstash-redis` Python package.
- **Layer A — Full Report cache** keyed by lowercased username, TTL 6h. The biggest user-facing latency win.
- **Layer B — Singleflight lock** keyed by `lock:report:<user>` (TTL 30s, poll wait 25s) so concurrent cold-cache requests for the same username don't fan out into duplicate ingest jobs.
- **Layer C — GitHub API response cache** keyed by URL+params hash, per-endpoint TTLs (`/users/{u}` 1h, repos 15min, languages 1h, contents 30min, commits 5min, GraphQL 15min). Stretches the 5000/hr per-user GH rate-limit budget.
- **Layer D — Narrative cache + daily budget shared via Upstash** so cache hits work across Fluid Compute instances and the daily quota is enforced globally rather than per-instance.
- **Fail-open** on every cache layer — any Upstash error logs and falls through to the live path. The cache is a perf optimisation, never a correctness boundary.
- `GET /health` reports `cache: "up" | "down"` so a flapping Redis surfaces at the front door.

**Out of scope (deferred):**
- Frontend perf budget (TTI / LCP / CLS) — moved to **v0.7.1** as a focused frontend slice.
- Cron-driven background re-ingestion + manual "Force refresh" button — moved to **v0.8.0** where Sentry lands; silent cron failures need observability first.
- Rate limiting per-IP / per-user — stays in v0.9.0 Beta hardening.

**Exit criteria:**
- [x] Upstash Redis DB provisioned; `UPSTASH_REDIS_REST_URL` + `UPSTASH_REDIS_REST_TOKEN` set on Vercel Preview + Production. Live `/health` reports `cache: "up"` (verified 2026-05-21).
- [x] `GET /health` reports `cache: "up" | "down" | "unconfigured"`.
- [ ] Two consecutive `/analyze/{user}` requests on a warm deploy: second runs in ≤ 200ms p95. *(verified post-deploy with Upstash provisioned — p95 measurement still pending)*
- [x] `RedisCache` unit tests = 13; `singleflight()` unit tests = 6; total new tests = 55.
- [x] Cold + warm `get_report_for_user` integration test: second call skips `_live_ingest` entirely (Layer A hit).
- [x] `NarrativeCache` and `DailyBudget` work against both Redis (when configured) and in-process (when not).
- [x] Fault-injection test: all Upstash failures fall through; no 5xx caused by cache trouble.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.7.0`.

---

## v0.7.1 — Performance (frontend)

**Goal:** The `/u/[username]` page hits Lighthouse mobile ≥ 95 and meets a Core Web Vitals budget on 4G.

**Slice scope:**
- Lighthouse mobile audit on `/u/[username]` (signed-out + signed-in) and `/share/[slug]`.
- Frontend perf wins: image sizing on avatars, font-display strategy, lazy `framer-motion` LazyMotion already in place — audit + tune, don't rewrite.
- Bundle-size pass: check what's in the initial JS for `/u/[username]` and trim if a route is pulling unneeded vendor code.
- `cache: "force-cache"` and Next 16 `unstable_cache` (or the new cache-components API) where appropriate for static data.
- TTI / LCP / CLS measurement automated via Lighthouse CI on Vercel preview deploys (optional — fine to manual-measure if CI integration is heavy).

**Exit criteria (initial — see below for correction):**
- [x] Frontend optimizations landed (LazyMotion shrink, optimizePackageImports, next/image avatars).
- [~] Lighthouse mobile performance ≥ 95 on `/u/{user}`: **partial pass — prod median 90.** Localhost showed 94 but localhost has no real-network latency.
- [~] TTI ≤ 2.5s: **partial — prod 2,866 ms (+366 ms).**
- [~] LCP ≤ 2.5s: **partial — prod 2,804 ms (+304 ms).** CLS **0.080** passes (≤ 0.1).
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.7.1`.

**Sub-plan:** [`docs/superpowers/plans/2026-05-21-v0.7.1-frontend-perf.md`](./docs/superpowers/plans/2026-05-21-v0.7.1-frontend-perf.md) — 8 tasks, 7 landed, 1 deferred (ISR on `/share/[slug]` → v0.8.0 with on-demand revalidation). Measurements: [baseline](./docs/superpowers/measurements/2026-05-21-v0.7.1-baseline.md), [final](./docs/superpowers/measurements/2026-05-21-v0.7.1-final.md) (see "CORRECTION" section for prod-certified numbers).

**Methodology lesson:** Localhost `next start` + simulated 4G isn't enough to certify a prod perf budget — the network-latency gap is ~800 ms on LCP. v0.7.2 (below) closes the gap; v0.8.0+ perf work certifies against the live deploy URL.

---

## v0.7.2 — Perf gap-closer (post-v0.7.1 correction)

**Goal:** Close the v0.7.1 budget gap on the live deploy. Prod median (verified 2026-05-21): perf 90/95, LCP 2,804/2,500ms, TTI 2,866/2,500ms. Need to find ~310ms of LCP and ~370ms of TTI, push perf score to ≥95, and fix the deterministic 0.080 anonymous CLS.

**Why this is its own slice:** Honest accounting. v0.7.1 already shipped + tagged based on optimistic localhost measurements. Re-tagging would muddy the release timeline; a focused v0.7.2 with better methodology is cleaner. Also makes the localhost-vs-prod measurement lesson explicit.

**Slice scope:**
- **Identify the prod LCP element.** Lighthouse CLI returned `n/a` for selector — use PageSpeed Insights or Chrome DevTools Performance panel against `https://skill-issue-tau.vercel.app/u/octocat` to extract the actual LCP node. Likely candidates: the aggregate-score number (text), the SVG circle's final stroke state, or the engineering-report panel's headline.
- **Identify the 0.080 anonymous-viewer CLS source.** Reproducible to four decimals (0.080114 across 3 runs), so it's a specific element shifting. NOT the avatars (anonymous viewers don't render them). Candidates: `PositionBar` rendering after a measurement, `BadgeRow`'s flex wrap on narrow viewports, the `NarrativeCard` loading skeleton → streaming text swap, the `SaveShareControls` "sign in CTA" appearing after the session check.
- **Targeted fix per finding** — likely one or two of: dynamic-import below-fold components (`NarrativeCard`, scoring matrix), reserve space for components that mount after auth check, defer the SVG circle animation if it's the LCP, prefetch the LCP font.
- **Certify against live deploy.** 3-run median on `https://skill-issue-tau.vercel.app/u/octocat` after the fix; record in a new measurement report `docs/superpowers/measurements/<date>-v0.7.2-prod-certified.md`.

**Exit criteria:**
- [~] Prod 5-run median: **performance 94** on `/u/octocat` (target 95, 2/5 runs hit 95+). 1 point short at the Lighthouse noise floor.
- [~] Prod LCP **2,773 ms** (target ≤ 2,500, +273) and TTI **2,816 ms** (target ≤ 2,500, +316). Improved over v0.7.1 but still over the strict budget.
- [x] Prod CLS root cause documented + **CLS = 0** (target ≤ 0.05). Two shifts identified (loading-skeleton misalignment + SiteHeader Suspense fallback), both eliminated.
- [x] Measurement report committed: [`docs/superpowers/measurements/2026-05-21-v0.7.2-prod-certified.md`](./docs/superpowers/measurements/2026-05-21-v0.7.2-prod-certified.md).
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.7.2`.

**Decision:** Ship with the CLS structural fix as the headline win and document the remaining LCP gap. The strict-Lighthouse-budget chase has diminishing returns vs the noise floor of lighthouse-on-localhost-against-prod-URL. Real-user metrics from v0.8.0's Sentry/PostHog will give a much tighter signal for the remaining ~10% gap on LCP/TTI.

**Out of scope:** the deferred `/share/[slug]` ISR + on-demand revalidation hook — still belongs to v0.8.0 because it needs the backend↔frontend invalidation channel.

---

## v0.8.0 — Polish + observability

**Goal:** By the end of this slice we can answer three questions in production: what broke (Sentry), what did users actually do (PostHog + web vitals), and is the page accessible (axe = 0 critical). Nothing else.

**Design spec:** [`docs/superpowers/specs/2026-05-22-v0.8.0-polish-observability-design.md`](./docs/superpowers/specs/2026-05-22-v0.8.0-polish-observability-design.md).

**Slice scope (locked 2026-05-22):**
- **Backend observability** — `structlog` JSON logging + request-ID middleware + Sentry FE/BE init with PII scrub hook.
- **Frontend observability** — Sentry browser SDK via `instrumentation.ts`; PostHog browser SDK with auto-pageviews + web-vitals capture (RUM, replaces the deferred Speed Insights idea — free-free 12-month retention vs Speed Insights' 30-day Hobby cap).
- **Named PostHog events** — `analyze_submitted`, `share_toggled`, `share_card_copied`, `mode_toggled`, `sign_in_clicked`.
- **On-voice failure pages** — new `app/not-found.tsx`; refresh `app/error.tsx` copy + add `Sentry.captureException` hook.
- **Empty-state + skeleton audit** — verify `/me`, `/u/[username]/card`, `/share/[slug]` already have appropriate states (most do post-v0.7.2).
- **Accessibility pass** — `@axe-core/cli` against `/`, `/u/octocat`, `/u/octocat/card`, `/me`, `/share/<slug>`; fix all criticals.
- **Error budget doc** — `docs/OBSERVABILITY.md` defining critical-vs-acceptable classes + alert intent (rules wired later in a v0.8.x patch).

**Deferred to v0.8.x patches:**
- Cron daily re-ingestion → v0.8.1
- Manual "Force refresh" + `DELETE /me/cache/{username}` → v0.8.2
- On-demand `revalidateTag` for `/share/[slug]` ISR → v0.8.4 (was v0.8.3, shifted by the v0.8.3 empty-repo hotfix)
- `vercel.json` → `vercel.ts` migration → v0.8.5 (was v0.8.4, shifted by the v0.8.3 empty-repo hotfix)
- Sentry alert-rule wiring → v0.8.x once real error rates are known
- CI integration of `@axe-core/cli` → v0.8.x

Each deferred item is independent and earns its own patch release, matching the v0.7.x cadence.

**Exit criteria:**
- [x] Backend Sentry catches a deliberate test exception with `request_id` tag attached; no PII in the event body.
- [x] Frontend Sentry catches a deliberate client throw with source-mapped stack.
- [x] PostHog dashboard shows all 5 named events flowing from prod within 24h of deploy.
- [x] PostHog web-vitals capture identifies the prod LCP element on `/u/[username]` (closes v0.7.2's open gap).
- [x] `npx @axe-core/cli` returns zero critical issues on all 5 audited routes.
- [x] `docs/OBSERVABILITY.md` exists; defines critical vs acceptable error classes + alert intent.
- [x] PII contract (spec §6) verified by test for every listed field.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.8.0` tagged + released.

---

## v0.8.1 — Cron daily re-ingestion (deferred from v0.8.0)

**Goal:** Saved analyses refresh themselves overnight so a user who comes back tomorrow doesn't see stale data. Failures are visible because v0.8.0's Sentry is already in place.

**Design spec:** [`docs/superpowers/specs/2026-05-22-v0.8.1-cron-reingest-design.md`](./docs/superpowers/specs/2026-05-22-v0.8.1-cron-reingest-design.md).

**Slice scope (locked 2026-05-22):**
- Vercel Cron entry in `vercel.json` (folds into v0.8.5's `vercel.ts` migration later) hitting a new bearer-authed backend route `POST /cron/refresh-saved-analyses` at 03:00 UTC.
- Refresh target: **all** saved analyses (every row in `analyses`), oldest-not-refreshed-in-24h first.
- Chunk cap: N=25 per fire, 240s wall-clock budget (60s safety margin under Vercel's 300s timeout). Overflow spills to tomorrow — no self-invocation, no resume tokens (YAGNI applied).
- Token strategy: owner's latest unexpired session token (v0.5.0 encryption boundary), falling back to `GITHUB_TOKEN`. Decrypted per request, never logged.
- Cache strategy: write-through via existing `get_report_for_user` — Layer A Redis dedupe means multi-user saves of the same target only cost one GH fetch.
- No narrative pre-warming (would burn LLM budget against an uncertain "user returns tomorrow AND reads narrative" prior).
- Sentry breadcrumb per attempt; capture on rate-limit cliff (403) or DB error.

**Exit criteria:**
- [x] `POST /cron/refresh-saved-analyses` without auth header → 401.
- [x] With correct bearer + `TEST_DATABASE_URL` set → 200, summary JSON shape per spec §5.
- [x] One bad analysis (404 / RuntimeError) doesn't block subsequent rows.
- [x] A new `analysis_runs` row appears for each successfully-refreshed analysis; Layer A Redis populated. (Layer A write delegated to `_fetch_report`; contract covered by `tests/cron/test_cache_writethrough.py` + the existing `tests/test_report_cache.py`. `record_run` end-to-end covered by `tests/persistence/test_analyses.py::test_record_run_attaches_run_and_updates_latest` + the new wiring through `_record_run`.)
- [x] Wall-clock cap honored; 403 rate-limit cliff stops the chunk + triggers a Sentry capture. (Sentry capture is the `logger.error("cron rate_limit_cliff ...")` line + the structlog → Sentry integration.)
- [x] `vercel.json` declares the cron entry; `CRON_SECRET` documented in `docs/DEPLOY.md`.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.8.1`.

**Sub-plan:** When implementation starts, generate the TDD plan via `superpowers:writing-plans` against the spec; save to `docs/superpowers/plans/2026-05-22-v0.8.1-cron-reingest.md`. Expect ~10-12 tasks per spec §11 ordering.

---

## v0.8.2 — Manual "Force refresh" (shipped 2026-05-23)

**Goal:** Signed-in users can synchronously re-ingest any of their saved analyses from `/me` — no waiting for tonight's cron.

**Design spec:** [`docs/superpowers/specs/2026-05-22-v0.8.2-force-refresh-design.md`](./docs/superpowers/specs/2026-05-22-v0.8.2-force-refresh-design.md).

**Slice scope (locked + shipped 2026-05-23):**
- Backend `POST /me/refresh/{username}` — auth-required, ownership-strict (must be in caller's `analyses`), 10/hour per-user rate limit via Upstash `INCR` + `EXPIRE`. Invalidates Layer A `report:<lowercase>` key, runs the existing `get_report_for_user` pipeline cold, writes a new `analysis_runs` row, returns the fresh Report inline.
- Frontend `<RefreshButton>` client component embedded in `<HistoryCard>` — `idle → pending → success | error | rate_limited` state machine; `e.preventDefault()` stops nested-Link navigation. PostHog `force_refresh_clicked` event tracks every settled state.
- Generic `app/cache/rate_limit.py::try_increment_counter` reusable for v0.9.0's other limits.

**Exit criteria:**
- [x] `POST /me/refresh/{username}` without cookie → 401.
- [x] Signed-in user requests target they never saved → 404 `no_saved_analysis`.
- [x] 11th call in the same UTC hour returns 429 with populated `Retry-After` header.
- [x] Happy path returns the Report JSON and writes a new `analysis_runs` row.
- [x] Cache delete failure doesn't break the route (fail-open verified by FakeRedis `fail_next` injection).
- [x] `/me` grid renders a Refresh button per row; click cycles through pending → success.
- [x] PostHog `force_refresh_clicked` event fires with `{target_login, duration_ms, success}`.
- [x] `docs/OBSERVABILITY.md` documents the new event.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version bumped to `0.8.2`.

**Sub-plan:** [`docs/superpowers/plans/2026-05-22-v0.8.2-force-refresh.md`](./docs/superpowers/plans/2026-05-22-v0.8.2-force-refresh.md) — 10 tasks, all shipped.

---

## v0.8.3 — Hotfix: empty-repo 409 (shipped 2026-05-24)

**Goal:** Analysing GitHub users with empty repositories must not crash. Real-user `mohit-sharma2` failure surfaced via Sentry against `release=0.8.2`.

**Root cause:** GitHub returns `409 Conflict — "Git Repository is empty."` (not 404) on `/contents` and `/commits` endpoints when a repo has zero commits. The ingestion fan-out blew up on the first 409.

**Slice scope (shipped):**
- Five `GitHubClient` methods patched to treat 409 as graceful empty-result, same as 404: `list_commits`, `list_recent_commits_sample`, `get_repo_root_contents`, `list_workflow_files`, `get_repo_readme_text`. Plus `get_license` defensively.
- `_CACHEABLE_STATUSES` adds `409` so subsequent ingest skips the round-trip for known-empty repos.
- 3 new respx tests cover the 409 path; existing 404 test kept for defence-in-depth.

**Exit criteria:**
- [x] Real-user `mohit-sharma2` analysis no longer 5xx's (verified post-deploy by re-analysis).
- [x] All 5 client methods that hit /repos/{owner}/{repo}/contents-or-commits-or-readme treat 409 as empty.
- [x] 409 cached alongside 404/200/422.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version bumped to `0.8.3`.

---

## v0.8.4 — Hotfix: narrative persistence honesty (shipped 2026-05-25)

**Goal:** Persisted narratives must record the right provider and the right `is_fallback`. Real-user analytics need to be able to ask "what % of narratives served last week came from the deterministic fallback?" and "how much of our traffic actually went to Groq vs OpenAI?" — both queries returned wrong answers before this slice.

**Root cause:** Two stale values in `app/routers/narrative.py`'s SSE persistence path:
1. `provider="openai"` was hardcoded despite Groq being the production default since v0.5.0 (2026-05-18).
2. `is_fallback = False` was declared locally and never re-assigned, even when `NarrativeService.stream_narrative` switched to the deterministic fallback. The flag was always written `False`.

The narrative-mode CHECK constraint was a third drift in the same family — the v0.5.0 schema allowed `'recruiter','cto','career'` modes that were product-dropped in v0.6.0 (2026-05-19). No follow-up migration trimmed them.

**Slice scope (shipped):**
- `app/narrative/service.py`: new `NarrativeStreamMeta` dataclass. `stream_narrative` accepts an optional `meta: NarrativeStreamMeta` kwarg and writes `is_fallback` / `fallback_reason` / `cache_hit` through it. Per-request state, no race against the `@lru_cache`-singleton `NarrativeService`.
- `app/routers/narrative.py`: instantiates `NarrativeStreamMeta` per request, passes it through, reads it after the stream finishes. `provider` derived via new `_resolve_provider(base_url)` helper (groq / openai / openrouter / cerebras / openai-compatible). `model_name` set to `NULL` on fallback rows.
- New Alembic migration `20260525_0002_trim_narrative_mode_check.py` — drop + recreate `ck_narratives_mode` with `('roast','mentor')` only. Reversible.
- Model `app/db/models.py::Narrative` mirrors the new constraint.
- `app/github/client.py` `User-Agent` derives from `app.settings.VERSION` (was frozen at `0.1.0`).

**Exit criteria:**
- [x] `NarrativeService.stream_narrative(..., meta=meta)` writes `meta.is_fallback=True` on both budget-exhaust and LLM-error paths; `False` on cache-hit and successful live stream.
- [x] `_resolve_provider(None)` → `"openai"`; `_resolve_provider("https://api.groq.com/openai/v1")` → `"groq"`; unknown host → `"openai-compatible"`.
- [x] Alembic `upgrade head` then `downgrade base` round-trips cleanly on a fresh Neon branch.
- [x] `GET /health` reports `version: 0.8.4` after deploy; outbound GH calls send `User-Agent: skill-issue/0.8.4`.
- [x] 13 new tests pass (4 service meta + 9 provider parametrized). Suite 243 → 256 non-DB-fixture.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version bumped to `0.8.4`.

---

## v0.8.5 — CI pipeline + dep cleanup (shipped 2026-05-25)

**Goal:** Close the v0.8.3-style "ship a regression, learn about it from Sentry post-deploy" loop by exercising the whole test + lint + build stack pre-merge.

**Slice scope (shipped):**
- New `.github/workflows/ci.yml`: backend job (`uv sync --frozen --dev` → `ruff check` → `ruff format --check` → `pytest -q`) + frontend job (`npm ci` → `npm run lint` → `npx tsc --noEmit` → `npm run test:run` → `npm run build`). Runs on every PR and every push to `main`. Concurrency group cancels stale runs on the same ref.
- `backend/requirements.txt` regenerated via `uv export --no-hashes --no-dev` so it carries all 15 direct deps + transitive closure (138 lines, was 82). Prior `requirements.txt` was missing 9 of 15 direct deps — production survived only because `@vercel/python` resolves through `pyproject.toml` + `uv.lock`.

**Exit criteria:**
- [x] CI workflow runs on PR + push-to-main; concurrency group cancels stale runs.
- [x] Both backend and frontend jobs pass on the v0.8.5 commit.
- [x] `requirements.txt` contains `alembic`, `asyncpg`, `authlib`, `cryptography`, `openai`, `sentry-sdk`, `sqlalchemy`, `structlog`, `upstash-redis`.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version bumped to `0.8.5`.

**Deferred to a v0.8.x patch:**
- DB-fixture tests in CI need a `services: postgres:` block + `TEST_DATABASE_URL`; pairs with Neon branch-per-PR provisioning (out of scope here).

---

## v0.8.6 — On-demand `revalidateTag` for `/share/[slug]` ISR (deferred from v0.7.1)

**Goal:** Public share pages render from a per-slug Next 16 Cache Components cache; backend share-toggle endpoints synchronously bust the tag via a shared-secret webhook. A revoked slug 404s on the next request — no stale window. Closes v0.7.1's deferral.

**Design spec:** [`docs/superpowers/specs/2026-05-25-v0.8.6-share-isr-design.md`](./docs/superpowers/specs/2026-05-25-v0.8.6-share-isr-design.md).

**Sub-plan:** [`docs/superpowers/plans/2026-05-25-v0.8.6-share-isr.md`](./docs/superpowers/plans/2026-05-25-v0.8.6-share-isr.md) — 9 tasks, TDD-ordered.

**Slice scope (locked 2026-05-25):**
- `/share/[slug]/page.tsx` and `/share/[slug]/opengraph-image.tsx` migrate from `force-dynamic` to `'use cache'` + `cacheTag(\`share:${slug}\`)` + `cacheLife({ revalidate: 3600 })`. 3600s is a fallback only — the webhook is the primary invalidation path.
- New `frontend/src/app/api/revalidate/route.ts` — POST with `X-Revalidate-Secret` + `{tag: "share:<slug>"}`. Constant-time secret compare, regex-validated tag (`^share:[A-Za-z0-9_-]{1,64}$`), calls `revalidateTag`, returns 204.
- New `backend/app/share/webhook.py::revalidate_share_slug(slug)` — fire-and-forget POST scheduled via FastAPI `BackgroundTasks` after every `set_share_slug` / `revoke_share_slug`. 5 s timeout. All failures logged + swallowed (Sentry breadcrumb); the toggle's HTTP response never blocks on it.
- `revoke_share_slug` return signature changes from `None` → `str` so the caller can pass the just-removed slug to the webhook.
- Two new env vars: `FRONTEND_BASE_URL` (backend) and `REVALIDATE_SECRET` (both sides). Either unset = graceful degradation: cacheLife absorbs the gap. Provisioning gate before tag.

**Exit criteria:**
- [x] `revalidate_share_slug` is a no-op + warning-log when either env var is unset.
- [x] `revalidate_share_slug` POSTs the expected URL / headers / body when both are set; 4xx + timeout swallowed.
- [x] `share_analysis` + `revoke_share` enqueue the webhook via `BackgroundTasks`; DB-fixture tests assert the task fires with the right slug.
- [x] `revoke_share_slug` returns the removed slug string.
- [x] Frontend `/api/revalidate` returns 401 on missing/wrong secret, 400 on bad tag, 204 + `revalidateTag` called on valid request.
- [x] `/share/[slug]/page.tsx` no longer carries `force-dynamic`; build output confirms `◐ Partial Prerender` treatment. Live revoke → 404 verification post-deploy.
- [x] `/share/[slug]/opengraph-image.tsx` uses the same cache tag (transitively via `fetchReportForSlug` → `fetchSharedPayload`) so social previews invalidate alongside the page.
- [x] 14 new tests pass (5 webhook + 1 persistence + 3 share-router + 5 frontend). Suite 256 → 261 backend non-DB; 37 → 42 frontend vitest.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version bumped to `0.8.6`.

---

## v0.8.7 — `vercel.json` → `vercel.ts` migration (shipped 2026-05-26)

**Goal:** Track the 2026-02-27 Vercel knowledge update by moving the project config to typed TypeScript.

**Design spec:** [`docs/superpowers/specs/2026-05-26-v0.8.7-vercel-ts-design.md`](./docs/superpowers/specs/2026-05-26-v0.8.7-vercel-ts-design.md).
**Sub-plan:** [`docs/superpowers/plans/2026-05-26-v0.8.7-vercel-ts.md`](./docs/superpowers/plans/2026-05-26-v0.8.7-vercel-ts.md) — 6 tasks, config-only (no runtime tests).

**Slice scope (shipped):**
- Root `vercel.json` ported to `vercel.ts` using `@vercel/config/v1`. All three keys (`experimentalServices`, `crons`, `git.deploymentEnabled`) preserved literally. `@vercel/config@0.5.0` already types `experimentalServices` — no intersection-type fallback was needed.
- New root `package.json` declares `@vercel/config` + `typescript` as devDeps. New root `tsconfig.json` scoped to `vercel.ts`.
- New CI job `Config (vercel.ts typecheck)` runs `tsc --noEmit -p .` at repo root on every PR.
- `backend/vercel.json` untouched.

**Exit criteria:**
- [x] Root `vercel.ts` exists; TSC clean (`npx tsc --noEmit -p .`).
- [x] Root `package.json` declares `@vercel/config` as a devDep; `npm ci` resolves cleanly.
- [x] Root `package-lock.json` committed.
- [x] Root `tsconfig.json` minimal, scoped to `vercel.ts`.
- [x] Root `vercel.json` deleted; `backend/vercel.json` untouched.
- [x] CI's new `config` job green on the PR.
- [x] `feat/v0.8.7-vercel-ts` did NOT auto-deploy a Preview — confirms `git.deploymentEnabled` filter survived.
- [ ] Post-merge prod deploy: `/health` reports `version: 0.8.7`; sign-in, `/u/octocat`, `/share/<slug>` all verified.
- [x] `CHANGELOG.md` `[0.8.7]` written user-facing; `docs/PROGRESS_LOG.md` entry committed; `PLAN.md` row flipped ✅.
- [ ] Tag `v0.8.7` pushed; release workflow published the GitHub Release.

---

## v0.9.0 — Bounded GH fan-out (shipped 2026-05-26)

**Goal:** Cap concurrent GitHub API calls inside `ingest_profile` to `settings.gh_ingest_concurrency` (default 8) so a single analysis can't burst past GitHub's secondary rate-limit threshold. Opens the v0.9.x Beta hardening family.

**Design spec:** [`docs/superpowers/specs/2026-05-26-v0.9.0-bounded-fanout-design.md`](./docs/superpowers/specs/2026-05-26-v0.9.0-bounded-fanout-design.md).
**Sub-plan:** [`docs/superpowers/plans/2026-05-26-v0.9.0-bounded-fanout.md`](./docs/superpowers/plans/2026-05-26-v0.9.0-bounded-fanout.md) — 4 tasks, TDD-ordered.

**Slice scope (shipped):**
- New `Settings.gh_ingest_concurrency: int = 8` field (env override `GH_INGEST_CONCURRENCY`).
- New file-local `_gated(sem, coro)` helper in `app/ingestion/profile.py` (Python 3.12 PEP 695 generic syntax).
- Both `asyncio.gather` blocks in `ingest_profile` wrapped via `_gated`. One semaphore per call, reused across both blocks (block 1 fully drains before block 2 starts).
- Sequential `list_languages` loop intentionally untouched (already bounded by construction).
- 2 new tests against a `FakeGitHubClient` instrument the in-flight count across a 50-repo synthetic profile.

**Exit criteria:**
- [x] `Settings.gh_ingest_concurrency` field exists with default 8.
- [x] `_gated` helper added; both gather blocks use it.
- [x] `test_bounded_fanout_default_cap` passes (max in-flight ≤ 8).
- [x] `test_bounded_fanout_overridable_via_settings` passes (max in-flight ≤ 2 with override).
- [x] Backend `pytest -q` non-DB suite: 263 passed.
- [x] `ruff check .` + `ruff format --check .` clean.
- [x] CI green on PR.
- [ ] Post-merge prod `/health` reports `version: 0.9.0`; one live `/analyze/octocat` returns a valid Report.
- [x] `CHANGELOG.md` `[0.9.0]` + `docs/PROGRESS_LOG.md` entry + PLAN row flipped ✅.
- [ ] Tag `v0.9.0` pushed; release workflow published the GitHub Release.

---

## v0.9.1 — `/me/analyses` N+1 fix + Layer A cache schema version (shipped 2026-05-27)

**Goal:** Two tiny perf patches batched per the 2026-05-26 v0.9.x decomposition. (1) Eliminate the per-row `SELECT AnalysisRun` in `/me/analyses`. (2) Namespace the Layer A Report cache key with `REPORT_SCHEMA_VERSION`.

**Design spec:** [`docs/superpowers/specs/2026-05-27-v0.9.1-perf-batch-design.md`](./docs/superpowers/specs/2026-05-27-v0.9.1-perf-batch-design.md).
**Sub-plan:** [`docs/superpowers/plans/2026-05-27-v0.9.1-perf-batch.md`](./docs/superpowers/plans/2026-05-27-v0.9.1-perf-batch.md) — 4 tasks, TDD-ordered.

**Slice scope (shipped):**
- `list_user_analyses` return type: `tuple[list[Analysis], int]` → `tuple[list[tuple[Analysis, AnalysisRun | None]], int]`. The query already JOINed `aliased(AnalysisRun)`; it now surfaces the join instead of discarding it.
- `/me/analyses` route: `for a, run in rows:` (one query per page total, no inner `db.scalar`). JSON contract unchanged.
- `REPORT_SCHEMA_VERSION = 1` in `app/cache/keys.py`. `report_key(username)` returns `f"v{REPORT_SCHEMA_VERSION}:{username.lower()}"`. Final key: `si:v1:report:v1:octocat`.
- 2 new unit tests + 1 existing test updated. 2 DB-fixture tests updated to unpack the new tuple shape.

**Exit criteria:**
- [x] `list_user_analyses` returns `tuple[list[tuple[Analysis, AnalysisRun | None]], int]`.
- [x] `/me/analyses` serializer no longer issues a per-row `SELECT AnalysisRun`.
- [x] `REPORT_SCHEMA_VERSION = 1` exists; `report_key("octocat") == "v1:octocat"`.
- [x] Bump-rewrites-key behavior covered by `test_report_key_bump_rewrites_namespace`.
- [x] Backend `pytest -q` non-DB suite: 265 passed (was 263; +2 net new cache tests, 1 existing-updated).
- [x] `ruff check .` + `ruff format --check .` clean.
- [x] CI green on PR.
- [ ] Post-merge prod `/health` reports `version: 0.9.1`; `/u/octocat` analyses cleanly.
- [x] `CHANGELOG.md` `[0.9.1]` + `docs/PROGRESS_LOG.md` entry + PLAN row flipped ✅.
- [ ] Tag `v0.9.1` pushed; release workflow published.

---

## v0.9.2 — Rate limiting (IP + user) (shipped 2026-05-27)

**Goal:** Cap `/analyze` and `/narrative` request volume so no single client can burn the shared GitHub-token quota, the DB, or the shared LLM budget. Anonymous callers are limited per-IP; signed-in callers per-user (they bring their own GitHub token).

**Design spec:** [`docs/superpowers/specs/2026-05-27-v0.9.2-rate-limiting-design.md`](./docs/superpowers/specs/2026-05-27-v0.9.2-rate-limiting-design.md).
**Sub-plan:** [`docs/superpowers/plans/2026-05-27-v0.9.2-rate-limiting.md`](./docs/superpowers/plans/2026-05-27-v0.9.2-rate-limiting.md) — 8 tasks, TDD-ordered.

**Slice scope (shipped):**
- `try_increment_counter` / `rate_limit_key` generalized from `user_id: int` to `subject: str` (`user:<id>` | `ip:<addr>`); the v0.8.2 force-refresh caller adapts.
- New `app/ratelimit.py`: `client_ip`, `is_trusted_proxy`, shared `hour_bucket` / `seconds_until_next_hour` time helpers (moved out of `refresh.py`), and a `make_rate_limiter` dependency factory. Auth-tier model: signed-in → per-user cap, anonymous → per-IP cap. Fail-open on Redis error or unconfigured cache.
- Defaults (env-overridable): anon 20 analyze/hr + 30 narrative/hr; signed-in 60 analyze/hr + 90 narrative/hr.
- Trusted-proxy header: the Next.js RSC forwards the real client IP (`X-Client-IP`) + a shared secret (`INTERNAL_PROXY_SECRET`); the backend trusts the forwarded IP only on a constant-time secret match. When the secret is unset, anonymous `/analyze` enforcement is skipped (so website visitors aren't collapsed into one Vercel-infra-IP bucket); narrative + signed-in limits stay active.
- 429 returns `{"error":"rate_limited","retry_after_seconds":N}` + `Retry-After` (the shared exception handler now forwards `exc.headers`). Frontend renders an on-voice "slow down" view instead of `error.tsx`.
- **Deferred to a later v0.9.x patch:** abuse heuristics / suspicious-username throttle, `/auth` throttling, per-day caps.

**Exit criteria:**
- [x] `rate_limit_key` / `try_increment_counter` take `subject: str`; `refresh.py` adapted; cache tests green.
- [x] Anonymous `/analyze` over the IP cap (secret configured) → 429 + `Retry-After`; under cap → 200.
- [x] Signed-in `/analyze` and `/narrative` limited per-user, independent of IP.
- [x] Anonymous `/narrative` over the IP cap → 429 (browser-direct, real IP).
- [x] `internal_proxy_secret` unset → anonymous `/analyze` enforcement skipped; narrative + user limits still active.
- [x] Spoofed `X-Client-IP` without a valid secret is ignored (falls back to connection IP).
- [x] Cache unconfigured / Redis error → fail-open.
- [x] Frontend renders an on-voice 429 view, not `error.tsx`.
- [x] `event=rate_limit.throttled` logged with no raw IP/user_id; documented in `OBSERVABILITY.md`.
- [x] Backend non-DB suite 281 pass; frontend 44 vitest pass; both lint/tsc/build clean.
- [ ] Post-merge prod `/health` reports `version: 0.9.2`; `INTERNAL_PROXY_SECRET` provisioned on both services.
- [x] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` + `PLAN.md` updated; version bumped to `0.9.2`.

---

## v0.9.3 — Deletable history + back-nav fix + creator flair (shipped 2026-05-28)

**Goal:** Three UX changes — delete a saved analysis from `/me` (with undo), fix the landing search spinner stuck after browser back-navigation, and give the project's **creator account** a golden treatment on the results page + shareable card (a generic "creator" distinction so whoever built the project is recognizable on their own report — not tied to any one person).

**Design spec:** [`docs/superpowers/specs/2026-05-27-v0.9.3-history-delete-and-creator-flair-design.md`](./docs/superpowers/specs/2026-05-27-v0.9.3-history-delete-and-creator-flair-design.md).
**Sub-plan:** [`docs/superpowers/plans/2026-05-27-v0.9.3-history-delete-and-creator-flair.md`](./docs/superpowers/plans/2026-05-27-v0.9.3-history-delete-and-creator-flair.md) — 8 tasks, TDD-ordered.

**Slice scope (shipped):**
- Backend `DELETE /analyses/{id}` (ownership-checked; DB cascade removes runs+narratives; busts the share cache when the analysis was public).
- `/me` grid → client `HistoryGrid` with optimistic remove + a single undo toast that defers the real delete ~5s.
- `search-bar.tsx` resets its loading flag on the `pageshow` (bfcache) event — fixes the stuck spinner after browser Back.
- A `creator-theme` class overrides `--accent` to gold for the creator account (gilds the score ring, chips, badges) + a "CREATOR · SKILL ISSUE" badge; the satori OG card gains a `creator` prop (static gold). The creator account is a single configurable login (`CREATOR_LOGIN`), not hard-wired to a person in the product copy. *(The glow/shimmer that originally shipped was removed same-day — it revealed the square panel bounds behind the ring and conflicts with the "no neon glow" design rule; see PROGRESS_LOG.)*

**Exit criteria:**
- [x] `DELETE /analyses/{id}` → 204 (owner), 403 (not owner); deleting a public analysis busts its share-page cache; runs + narratives cascade.
- [x] `/me` shows a ✕ per card; click removes + shows undo toast; Undo restores + issues no DELETE; timeout issues the DELETE.
- [x] Landing search button no longer stuck spinning after browser Back (bfcache `pageshow` reset); vitest covers it.
- [x] The creator account's report renders the gold accent + "CREATOR · SKILL ISSUE" badge; a normal user's page unchanged.
- [x] The creator account's shareable card + OG PNG render the gold palette + creator label.
- [x] Backend `ruff` + `pytest` clean; frontend `lint` + `tsc` + `test:run` + `build` clean.
- [x] `CHANGELOG.md` + `PLAN.md` + `docs/PROGRESS_LOG.md` updated; version bumped to `0.9.3`; pushed to `main`.

**Note:** the planned full-`ResultsView` render test was dropped — `next/dynamic` + `framer-motion` suspend the component under happy-dom, making it brittle. Per AGENTS ("UI does not need 100% coverage — visual verification is fine"), creator detection is covered by the `isCreator` unit test + `tsc`/`build` + visual check.

---

## v0.9.4 — DB pool size env-tunable + back-nav spinner fix (shipped 2026-05-28)

**Goal:** Make the SQLAlchemy engine's `pool_size` / `max_overflow` configurable via `DB_POOL_SIZE` / `DB_MAX_OVERFLOW`, keeping the 5/5 defaults. Plus a genuine fix for the landing-page search spinner sticking on browser-back (the v0.9.3 attempt fixed the wrong mechanism).

**Why not the planned 10/20 bump:** Direct telemetry on 2026-05-28 (Neon `max_connections=112`, ~1 live app connection; Vercel 0% error rate; Sentry clean) showed no pool-exhaustion symptom. A blind bump to 30 connections/instance would also risk the 105-usable ceiling under multi-instance Fluid Compute. So the slice ships tunability instead of a default change; flip the env var if RUM ever shows the symptom.

**Back-nav spinner root cause:** Cache Components (`cacheComponents: true`, shipped v0.8.6) keeps the landing page mounted in a hidden React `<Activity>` on navigation instead of unmounting it, so the manual `isLoading` `useState` was preserved and reappeared as a stuck spinner on browser-back. Fixed by switching `search-bar.tsx` to `useTransition` (pending state derived from the live navigation, idle on return by construction). The v0.9.3 `pageshow` listener was inert (same-document soft-nav never fires it) and its test was a false positive.

**Design spec:** [`docs/superpowers/specs/2026-05-28-v0.9.4-db-pool-tunable-design.md`](./docs/superpowers/specs/2026-05-28-v0.9.4-db-pool-tunable-design.md).
**Sub-plan:** [`docs/superpowers/plans/2026-05-28-v0.9.4-db-pool-tunable.md`](./docs/superpowers/plans/2026-05-28-v0.9.4-db-pool-tunable.md).

**Exit criteria:**
- [x] `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` settings (default 5); `_build_engine` reads them via the module reference.
- [x] 2 new non-DB tests (defaults + override) pass; backend suite 281 → 283.
- [x] `search-bar.tsx` uses `useTransition`; inert `pageshow` effect removed; bfcache test replaced with normalize/validation/nav coverage (frontend vitest 51 → 54).
- [x] Docs ritual + version bump to 0.9.4; tag + release.

---

## v0.9.5 — Security review + hardening (shipped 2026-05-28)

**Goal:** Full pre-launch security audit of the whole app; resolve any high/critical findings. (The load test was split out to v0.9.6 — it needs a deliberate target/cost/rate-limit-bypass design and is independently shippable.)

**Audit result:** No high or critical findings. Verified sound: authorization (every mutation ownership-checked via `_owned_analysis`, no IDOR), AES-GCM session-token encryption, OAuth `state` CSRF with constant-time compare, no SQL injection (SQLAlchemy constructs only), no XSS (no `dangerouslySetInnerHTML`; LLM narrative renders as escaped text), no SSRF (username regex-validated server-side; GitHub URLs built only from validated input + trusted API responses), server-only secrets.

**Fixes shipped (two Mediums):**
- **OAuth scope `read:user public_repo` → `read:user`.** `public_repo` is a *write* scope; reading public data needs none. Reduces a leaked stored token's blast radius. New logins only; existing sessions unaffected.
- **HTTP security headers** in `frontend/next.config.ts`: enforced `X-Frame-Options: SAMEORIGIN`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`; plus a **report-only** Content-Security-Policy (logs violations without blocking — to be tuned against real reports before enforcing).

**Operator follow-ups (config, no code):** verify `COOKIE_SECURE=true` in prod; confirm `CORS_ALLOW_ORIGIN_REGEX` is scoped to our own origins (not `*.vercel.app`).

**Exit criteria:**
- [x] Whole-app security audit completed; findings severity-ranked.
- [x] All high/critical findings resolved (none found).
- [x] OAuth scope tightened + test; security headers added; `next build` clean.
- [x] Docs ritual + version bump to 0.9.5; tag + release.

---

## v0.9.6 — Load-test harness (shipped 2026-05-28)

**Goal:** Reusable Python/httpx open-loop load harness for the backend warm `/analyze` path; the full 100 RPS validation run is an operator step (hardware-gated).

**Delivered:** `backend/loadtest/run.py` (open-loop dispatcher, p50/p95/p99, error rate, achieved RPS, pass/fail thresholds, ramp), unit-tested stats helpers, and `backend/loadtest/README.md` runbook (local SRH warm-cache setup + deploy target). Local warm-cache uses SRH (Upstash-compatible Redis over Docker) — real Upstash's ~10k/day free tier can't absorb a 100 RPS run. Anonymous load + unset `INTERNAL_PROXY_SECRET` means the analyze limiter skips enforcement, so no bypass is needed.

**Design spec:** [`docs/superpowers/specs/2026-05-28-v0.9.6-load-test-harness-design.md`](./docs/superpowers/specs/2026-05-28-v0.9.6-load-test-harness-design.md).
**Sub-plan:** [`docs/superpowers/plans/2026-05-28-v0.9.6-load-test-harness.md`](./docs/superpowers/plans/2026-05-28-v0.9.6-load-test-harness.md).

**Exit criteria:**
- [x] `loadtest/run.py` + unit-tested stats helpers; ruff clean; backend suite green.
- [x] Runbook complete (local SRH + deploy target).
- [x] Light `/health`-class sanity run passes (ran against `/openapi.json`: 10 RPS × 5 s, 0 errors, p95 6.2 ms, PASS).
- [x] Docs ritual + version bump to 0.9.6; tag + release.
- [ ] Full 100 RPS warm-`/analyze` result recorded — operator step, filled in when run.

---

## v0.9.7 — Privacy + Terms (shipped 2026-05-28)

**Goal:** Plain-language Privacy Policy + Terms of Service pages, linked from a new global footer.

**Delivered:** Static TSX pages `/privacy` + `/terms` (shared `LegalProse` wrapper), a global `SiteFooter`, content grounded in the app's real data practices (GitHub `read:user`, Neon, Upstash, Groq, Sentry, PostHog), India governing law, 13+, contact shaansatsangi.cse@gmail.com. Not legal advice — flagged for professional review before launch.

**Design spec:** [`docs/superpowers/specs/2026-05-28-v0.9.7-legal-docs-design.md`](./docs/superpowers/specs/2026-05-28-v0.9.7-legal-docs-design.md).
**Sub-plan:** [`docs/superpowers/plans/2026-05-28-v0.9.7-legal-docs.md`](./docs/superpowers/plans/2026-05-28-v0.9.7-legal-docs.md).

**Exit criteria:**
- [x] `/privacy` + `/terms` render via `LegalProse`; metadata + "Last updated 2026-05-28".
- [x] Global `SiteFooter` links both (+ GitHub); landing hero intact; mobile verified.
- [x] Smoke tests pass (3); frontend lint/tsc/test/build clean.
- [x] Docs ritual + version bump to 0.9.7; tag + release.

---

## v0.9.8 — Launch landing sections (shipped 2026-05-29)

**Goal:** Below-the-fold launch landing sections beneath the existing hero.

**Delivered:** `ExampleProfiles` (clickable example-profile cards → live `/u/<username>` reports — the honest proof), `HowItWorks` (deterministic-methodology feature grid), `StarCta` ("Star on GitHub" → repo). Hero/search/stats untouched; `/` still static-prerendered; responsive. No testimonials/usage-stats (none real). Shipped as v0.9.8, keeping 1.0.0 for the actual launch.

**Design spec:** [`docs/superpowers/specs/2026-05-28-v0.9.8-launch-landing-design.md`](./docs/superpowers/specs/2026-05-28-v0.9.8-launch-landing-design.md).
**Sub-plan:** [`docs/superpowers/plans/2026-05-28-v0.9.8-launch-landing.md`](./docs/superpowers/plans/2026-05-28-v0.9.8-launch-landing.md).

**Exit criteria:**
- [x] Three sections render beneath the hero; hero unchanged; `/` still static.
- [x] Example cards link to live reports; star CTA → repo (new tab).
- [x] Smoke test passes; frontend lint/tsc/test/build clean; mobile verified.
- [x] Docs ritual + version bump to 0.9.8; tag + release.

---

## v1.0.0 — First stable release (shipped 2026-05-29)

**Goal:** Cap the v0.9.x beta-hardening line as the first stable (1.0) release, with launch-readiness polish. The *public launch itself* (domain, posts, traffic) is operator-run, not a code milestone — tracked in [`docs/LAUNCH.md`](./docs/LAUNCH.md).

**Delivered (launch polish):** homepage Open Graph / Twitter link-preview cards (`app/opengraph-image.tsx` + `metadataBase`/`openGraph`/`twitter` in `layout.tsx`); desktop autofocus on the landing search (prop-gated so the results-page instance doesn't steal focus); an inline "analyze another" search on the report page (reuses `SearchBar`); removed unused Next starter svgs. The marketing landing sections shipped earlier in v0.9.8.

**Design spec / plan:** none — scope was locked directly with the user (the four polish items), implemented inline at the user's "make it v1.0.0 then ship it" direction.

**Exit criteria (code release):**
- [x] Launch-polish items implemented; frontend lint/tsc/test/build clean (58 vitest); backend 290.
- [x] Version bumped to `1.0.0` across literals; CHANGELOG `[1.0.0]`; tag + release.

**Public-launch ops (operator-run, see `docs/LAUNCH.md`):** production domain + SSL, launch posts (HN/X/Reddit/LinkedIn), 72h traffic watch, on-call notes, post-launch retro. Pre-launch reminders still open: professional legal review of `/privacy` + `/terms`; run the full 100 RPS load test.

---

## v1.0.1 — Launch Ops (GitHub Education perks)

**Goal:** Use the GitHub Student Developer Pack (received 2026-07) to clear the open launch blockers in [`docs/LAUNCH.md`](./docs/LAUNCH.md): production domain **skillissue.tech** (free year via the pack's .TECH offer), the 100 RPS load test on a DigitalOcean credit droplet, and the Sentry education plan with Session Replay enabled for launch-day watching.

**Design spec:** [`docs/superpowers/specs/2026-07-10-github-education-upgrades-design.md`](./docs/superpowers/specs/2026-07-10-github-education-upgrades-design.md) (§3).

**Shape:** operator checklist (redeem perks, register + cut over the domain, run the load test) + one small PR (Sentry replay/sampling config, host references in copy).

**Exit criteria:**
- [ ] skillissue.tech live with SSL; old vercel.app host redirects; OAuth verified end-to-end on the new domain.
- [ ] Test error produces a Sentry event with session replay attached.
- [ ] Load-test max RPS + p95 recorded in `docs/PROGRESS_LOG.md`.
- [ ] `CHANGELOG.md` `[1.0.1]`; tag `v1.0.1`; release.

---

## v1.0.2 — Security & hardening (audit remediation)

**Goal:** Remediate the findings of the 2026-07-13 full audit (repo + Vercel). Reliability + security patches only — no product features. Distinct from the v1.0.1 Launch-Ops slice.

**Shape:** one `fix/audit-hardening` branch, one commit per fix; no new user-facing surface.

**Delivered:**
- **Reliability:** the daily refresh cron was dead (Vercel GET vs POST-only handler → 405 every fire); now accepts GET, `maxDuration` 60→300 to clear the 240s chunk deadline.
- **Dependency CVEs:** 7 backend CVEs patched (starlette ×4, fastapi, cryptography, joserfc, pydantic-settings); frontend npm advisories 25→2 (remaining are moderate/build-time) incl. Vitest 3→4 + frontend minors.
- **App security:** `cookie_secure` fail-closed default; expired-session purge on the cron; username validation moved to the `_live_ingest` funnel; CSRF writes on GET `/analyze` + `/narrative` blocked via `Sec-Fetch-Site`.
- **Supply chain / CI:** Dependabot (npm/uv/actions); actions SHA-pinned; `release.yml` tag command-injection fixed; SCA gate (`npm audit` + `pip-audit`) added to CI.
- **Headers / hygiene:** HSTS `includeSubDomains; preload`; `unsafe-eval` dropped from (report-only) CSP; `.vercelignore`; `engines.node`; `CRON_SECRET` documented; `.gitignore` deduped.

**Exit criteria:**
- [ ] PR from `fix/audit-hardening` reviewed; CI green (incl. the new SCA gate); prod deploy verified (cron GET returns 200 with the bearer).
- [ ] `CHANGELOG.md` `[1.0.2]` (or merged into the v1.0.1 cut — operator's call); tag; release.

**Operator follow-ups (platform, not code — tracked in the 2026-07-13 PROGRESS_LOG entry):** Vercel WAF rate-limit on `/analyze*`+`/narrative*`, BotID, confirm `INTERNAL_PROXY_SECRET` set in prod, verify `CORS_ALLOW_ORIGIN_REGEX` scoped, `main` branch-protection ruleset, Vercel Spend alerts, hstspreload.org submission, and promoting CSP to enforcing.

---

## v1.0.3 — Hotfix: `/analyze` survives GitHub GraphQL resource limits (shipped 2026-07-18)

**Goal:** Stop `/analyze/{username}` 500-ing for hyper-active accounts (e.g. `antfu`) whose contribution data trips GitHub's GraphQL query-cost guard (`RESOURCE_LIMITS_EXCEEDED`). Surfaced by Sentry `SKILL-ISSUE-BACKEND-4` in production on `1.0.2`.

**Shape:** one `fix/analyze-graphql-resource-limits` branch; reliability only, no user-facing surface.

**Delivered:**
- **Client tolerates partial GraphQL responses** — `GitHubClient.graphql` now only raises when GitHub returns no `data` at all; a partial payload accompanied by a per-field `errors` entry is returned (with a warning logged) instead of being discarded.
- **Isolated the expensive field** — the `pullRequestReviewContributions.totalCount` read is split out of `EXTERNAL_PRS` into its own `EXTERNAL_REVIEW_COUNT` query, so a rejection there no longer takes the merged-PR count / account badges down with it.
- **Graceful degradation** — `_ingest_external_signals` fetches the two halves independently; any failure degrades that half to a conservative default (0 / False / empty) rather than failing the whole analysis.

**Exit criteria:**
- [x] Regression tests: partial-vs-fatal GraphQL branches, plus both degradation directions in ingestion. Full suite green (`295 passed`), ruff clean.
- [ ] PR reviewed; CI green; prod deploy verified against a whale account (`/analyze/antfu` returns 200).
- [ ] `CHANGELOG.md` `[1.0.3]`; tag `v1.0.3`; release. *(paused for operator go-ahead, per the slice workflow.)*

---

## v1.0.4 — Cost-control fairness & security hardening (audit Batch 1 + lower-risk Batch 2)

**Goal:** Remediate the cheap, low-risk cost & availability findings from the 2026-07-24 full security audit, plus the config/CI/observability quick wins. No user-facing feature changes.

**Design spec:** [`docs/superpowers/specs/2026-07-24-v1.0.4-cost-control-hardening-design.md`](./docs/superpowers/specs/2026-07-24-v1.0.4-cost-control-hardening-design.md). **Plan:** [`docs/superpowers/plans/2026-07-24-v1.0.4-cost-control-hardening.md`](./docs/superpowers/plans/2026-07-24-v1.0.4-cost-control-hardening.md).

**Shape:** one `fix/v1.0.4-cost-control-hardening` branch. 8 findings across the rate limiter, LLM budget, session decrypt, Sentry scrub, CI, and `.env.example`.

**Delivered:**
- **SI-02 — per-subject LLM budget.** Global daily ceiling (500) plus per-IP (10) and per-user (40) daily caps; a real LLM call runs only if both dimensions have room. Reserve-then-release keeps counters accurate.
- **SI-04 — spoof-proof client IP.** `client_ip()` trusts Vercel's overwritten `x-forwarded-for` (configurable via `TRUSTED_CLIENT_IP_HEADER`) and no longer trusts `x-real-ip`.
- **SI-05 — fail-closed anon `/analyze`.** When `INTERNAL_PROXY_SECRET` is unset, a conservative shared `ip:unattributed` backstop (300/hr) replaces the previous "skip".
- **SI-01 — fail-closed cost controls.** A cache outage degrades the rate limiter and LLM budget to conservative in-process fallbacks (`rate_limit.degraded_local` / `narrative.budget.degraded_local`) instead of unlimited.
- **SI-11 — Sentry scrub** of `x-internal-secret`, `x-revalidate-secret`, and IP headers (backend + frontend).
- **SI-12 — CI least privilege** (`permissions: contents: read`).
- **SI-13 — `.env.example`** no longer ships an active `COOKIE_SECURE=false`.
- **SI-22 — session decrypt** failure returns `None` (clean re-login) instead of a 500.

**Exit criteria:**
- [x] Backend `ruff` clean, `pytest -q` non-DB suite green (310 passed). Frontend `lint` + `tsc` + `test:run` + `build` clean.
- [ ] PR reviewed; CI green; prod deploy verified. *(paused for operator go-ahead before tag/release, per the slice workflow.)*
- [ ] `CHANGELOG.md` `[1.0.4]`; tag `v1.0.4`; release.

---

## v1.0.5 — Ingest amplification containment (cores)

**Goal:** Bound how much work one cold `/analyze` can trigger (audit Workstream C). Split from v1.0.4 so the hottest code got its own review/verify cycle. Scope decision (user): ship the **core** of each finding; defer the 3 complex **extensions** to v1.0.6.

**Design spec:** [`docs/superpowers/specs/2026-07-24-v1.0.5-ingest-amplification-containment-design.md`](./docs/superpowers/specs/2026-07-24-v1.0.5-ingest-amplification-containment-design.md). **Plan:** [`docs/superpowers/plans/2026-07-24-v1.0.5-ingest-amplification-containment.md`](./docs/superpowers/plans/2026-07-24-v1.0.5-ingest-amplification-containment.md).

**Delivered:**
- **SI-03** — per-analysis hard live-call cap (`GH_MAX_CALLS_PER_ANALYSIS=150`, ~1.5× the ~98 legit worst case) at the `GitHubClient._request` choke point; cache hits don't count → 503 `analysis_too_large`.
- **SI-06** — cap `Retry-After` (`10s`), parse HTTP-date safely, handle `429` (not just 403), + a `45s` ingest wall-clock deadline → 503 `analysis_timeout`.
- **SI-07** — `DailyBudget.arefund` + `try/except GeneratorExit` in the SSE router; refunds one slot on a mid-stream abort, only when truly consumed (captures the consumed UTC-day).
- **SI-08** — OG/card `fetchReportForUser` forwards `x-client-ip` + `x-internal-secret` so those ingests are attributed to the visitor IP and subject to the anon limiter.
- **SI-09** — holder-checked singleflight release (`delete_if_equals`) + `TTL_LOCK_SECONDS` 30→60.

**Exit criteria:**
- [x] Backend `ruff` clean, `pytest -q` non-DB suite green (321 passed). Frontend `lint` + `tsc` + `test:run` (70) + `build` clean.
- [ ] PR reviewed; CI green; prod deploy verified. *(paused for operator go-ahead before tag/release.)*
- [ ] `CHANGELOG.md` `[1.0.5]`; tag `v1.0.5`; release.

---

## v1.0.6 — Shared-token quota breaker

**Goal:** Close the platform-wide DoS the v1.0.5 per-analysis cap doesn't: ~30–50 concurrent distinct anon analyses can still drain the shared GitHub token's ~5000/hr, failing all anonymous analyses. Scope decision (user): ship **only** the quota breaker; drop/defer the other two deferred extensions.

**Design spec:** [`docs/superpowers/specs/2026-07-25-v1.0.6-shared-token-quota-breaker-design.md`](./docs/superpowers/specs/2026-07-25-v1.0.6-shared-token-quota-breaker-design.md). **Plan:** [`docs/superpowers/plans/2026-07-25-v1.0.6-shared-token-quota-breaker.md`](./docs/superpowers/plans/2026-07-25-v1.0.6-shared-token-quota-breaker.md).

**Delivered:**
- **SI-03 ext** — `GitHubClient` observes `X-RateLimit-Remaining` on live shared-token responses and writes a low-water mark to Redis (only below a 1000 watch threshold, so high-quota traffic is free). `_live_ingest` reads it and sheds new **anonymous** analyses with 503 `service_busy` when remaining is below `gh_shared_token_min_remaining` (default 500), before any GitHub call. Signed-in users (own token) bypass; cache-unavailable → breaker off (per-analysis cap still applies).

**Deferred / dropped (disposition of the other Workstream-C extensions):**
- **SI-07 ext (SSE stream coalescing) — DROPPED.** Marginal value (only helps concurrent same-profile+mode viewers in a seconds-wide window; the v1.0.5 abort-refund already closed the real abuse) versus high SSE-streaming complexity/risk.
- **SI-08 ext (OG store-gating) — DEFERRED (product decision).** Already contained by v1.0.5's OG attribution (OG ingests now hit the anon limiter). Store/cache-gating would change link-preview behavior for never-analyzed users (a growth-loop tradeoff); revisit only if desired.

**Exit criteria:**
- [x] Backend `ruff` clean, `pytest -q` non-DB suite green (327 passed). Frontend unchanged; gate green.
- [ ] PR reviewed; CI green; prod deploy verified. *(paused for operator go-ahead before tag/release.)*
- [ ] `CHANGELOG.md` `[1.0.6]`; tag `v1.0.6`; release.

---

## v1.1.0 — Progress Pulse (opt-in monthly score digest)

**Goal:** The retention loop. Signed-in users opt in (typed email, double opt-in — OAuth scope stays `read:user`) to a monthly email showing how their score moved: total/tier/bucket deltas + badges gained/lost, deterministic content only, no LLM. Email provider: originally the pack's Mailgun offer, but Sinch terminated new student claims (found 2026-07-11) — the slice's sender abstraction stands; pick a free-tier provider (likely Resend, 3K/mo) at implementation time, sending from `mg.skillissue.tech`. Implements the "Engineering Evolution Tracking" idea below in email form.

**Design spec:** [`docs/superpowers/specs/2026-07-10-github-education-upgrades-design.md`](./docs/superpowers/specs/2026-07-10-github-education-upgrades-design.md) (§4).

**Shape:** `email_subscriptions` table + `app/email/` (Mailgun via `httpx`, delta computation, template) + tokenized confirm/unsubscribe routes + daily due-based cron (`CRON_SECRET` pattern, per-sub fail-open, send only when something changed) + `/me` opt-in card + privacy-page clause.

**Exit criteria:**
- [ ] Opt-in → confirm → digest → unsubscribe loop verified in prod with a real inbox.
- [ ] Delta computation fully unit-tested (up/down/flat, tier change, badges, first digest).
- [ ] Mid-batch failure skips the sub, logs to Sentry, completes the rest.
- [ ] Privacy page updated; `CHANGELOG.md` `[1.1.0]`; tag `v1.1.0`; release.

---

## Beyond v1.0 — future ideas

Not committed. Tracked here so they don't get lost.

### Cross-platform identity expansion

The long-term play: Skill Issue is the *reputation layer for developers*, not a GitHub-only tool. Once GitHub analysis is stable in v1.0, the same deterministic-scoring + narrative architecture extends to other identity surfaces. These are major slices, each likely a `v1.X.0` family of its own.

- **GitLab Checker** — same six-bucket model, GitLab-native ingestion. Lowest-risk addition because the activity shape is closest to GitHub.
- **LinkedIn Profile Checker** — parse a LinkedIn export or public profile; score work history, role progression, endorsement signal. Different rubric, same explainability contract.
- **Resume Checker** — upload a PDF/markdown resume; score structure, signal density, stack relevance, evidence per claim. This is where the deterministic-vs-AI line gets interesting — resumes need extraction (LLM) before scoring (deterministic).

**Architecture implication for current work:** any abstractions added before v1.0 should make these extensions plausible without rewrites. In practice, that means keeping the *contract* clean (`Profile -> ScoreResult -> Report` is a generic shape), not building premature plugin systems.

### Other ideas

- **Recruiter / CTO / Career narrative modes** — originally slated for v0.6.0, dropped 2026-05-19. Roast + Mentor cover the comedic and constructive lanes; three more modes added prompt-template surface area without unlocking a distinct user need. Revisit if hiring partners or career-coach feedback explicitly asks for it post-v1.0.
- **Team Intelligence** — analyze an org's engineering identity
- **OSS Reputation Score** — public leaderboard for OSS contributors
- **Career Timeline** — animated history of a developer's growth
- **Hiring Mode** — recruiter dashboard with shortlists
- **Skill Graphs** — visualize stack expertise as a graph
- **Engineering Evolution Tracking** — month-over-month deltas → email form scheduled as **v1.1.0 Progress Pulse** above; richer in-app timelines remain a future idea

---

## Process notes for agents

1. **Pick a slice from the current version.** Do not jump ahead.
2. **Generate a TDD sub-plan** for the slice using the `superpowers:writing-plans` skill. Save to `docs/superpowers/plans/`.
3. **Implement task by task,** keeping commits small. No co-authoring.
4. **Update logs** as you go (`CHANGELOG.md` + `docs/PROGRESS_LOG.md`).
5. **Verify exit criteria** before bumping the version.
6. **Ask before** any new MCP/plugin permission or external account.
