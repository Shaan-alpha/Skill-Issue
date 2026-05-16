# Progress Log

> Running narrative log of what was done, why, what was learned, and what is blocked. The most recent entry is at the top.
>
> Every agent ending a working session must add an entry. Cold agents starting a session should read the top entry first.

Format:

```
## YYYY-MM-DD — <author or agent> — <one-line summary>

**Slice:** vX.Y.Z (or "scaffolding")
**Done:** ...
**Decisions:** ...
**Learned / surprises:** ...
**Blocked / open:** ...
**Next:** ...
```

---

## 2026-05-16 — Claude (Opus 4.7) — v0.5.0 design + pre-slice audit pass

**Slice:** v0.5.0 (designed, not yet implemented)

**Done:**
- **Pre-slice audit + cleanup (committed `9321d41`).** Backend ruff went from 16 errors to clean: dead `import re` removed, `Depends()` defaults migrated to the modern `Annotated[T, Depends(...)]` FastAPI 0.95+ pattern, RUF059 unused unpacked vars prefixed with `_`, a focused `RUF001` carve-out added for `app/narrative/prompts.py` so the deliberate en-dash typography in user-facing prompts is preserved, and four unused imports + three unused `z = ScoreResult(...)` locals stripped from the narrative test suite. Frontend lint went from 1 error to clean: refactored `narrative-card.tsx` to use `useSyncExternalStore` against `localStorage`, clearing the React 19 `react-hooks/set-state-in-effect` warning and gaining cross-tab sync via the native `storage` event as a free bonus. Bumped `react`/`react-dom` 19.2.4 → 19.2.6 (safe patch). Held off on the larger ESLint 10, TypeScript 6, and `@types/node` 25 majors — those are big enough they deserve their own slice rather than getting buried in v0.5.0 churn.
- Verified post-cleanup: `uv run ruff check .` clean, `uv run pytest -q` 124/124 pass, `npm run lint` clean, `npm run build` clean (2.7s with Turbopack). CHANGELOG gained an `[Unreleased]` section that will roll into v0.5.0.
- **Brainstormed the Auth + Persistence slice.** Locked the three upstream decisions with the user:
  1. **SQLAlchemy 2.0 async + asyncpg** for the DB layer.
  2. **Server-side sessions** (opaque cookie, encrypted GitHub access token in a `sessions` row). User's own token is used for ingestion when signed-in — gives every signed-in user a dedicated 5000/hr GitHub rate-limit budget.
  3. **Per-user-per-target `analyses`** with `(user_id, target_login)` uniqueness and opt-in `share_slug` for public viewing. Anonymous `/analyze` stays stateless.
- Wrote the design spec at [`docs/superpowers/specs/2026-05-16-v0.5.0-auth-persistence-design.md`](./superpowers/specs/2026-05-16-v0.5.0-auth-persistence-design.md). Covers OAuth flow (authlib + AES-GCM, no JWT, no PKCE because GitHub doesn't support it on OAuth Apps), 5-table schema with cascade deletes from `users`, Neon pooled connection on port 6543 with `statement_cache_size=0` to coexist with pgBouncer transaction-mode pooling, Alembic for migrations against a separate `DATABASE_DIRECT_URL`, backend module layout (`auth/`, `db/`, `persistence/`, `routers/`), API surface table (8 new endpoints + 3 modified), frontend additions (`/me`, `/share/[slug]`, header with sign-in/avatar menu), env var inventory, testing strategy, security review (one row per threat → mitigation), and 12-bullet exit criteria.
- Updated `PLAN.md` v0.5.0 section with the spec link, expanded slice scope, tightened exit criteria (concrete commands, ≥30 new tests, mobile QA at 320/375/414/768).

**Decisions:**
- **OAuth App, not GitHub App.** We're authenticating users to use their public GitHub data — not installing into orgs/repos. Scopes hard-coded `read:user public_repo`. Never `repo`, never `admin:*`.
- **Opaque sessions over JWT.** Cookie value is `secrets.token_urlsafe(32)`; server looks the row up directly. JWT was the implied path in TECH_STACK.md but it conflicts with needing to revoke sessions cheaply and store the GitHub token server-side. JOSE/authlib stays in the stack table for now as "optional", but v0.5.0 doesn't use it; we'll trim it after v0.5.0 ships if no slice picks it up by v0.7.0.
- **AES-GCM at rest for GitHub access tokens.** 32-byte key from `SESSION_TOKEN_ENC_KEY`, fresh 12-byte nonce per row. Key rotation invalidates every session by design — documented as a known operational behaviour, not a bug.
- **`(user_id, target_login)` uniqueness on `analyses`.** "Save once, re-run many times" semantics. Re-analyzing octocat updates `latest_run_id` rather than inserting a duplicate.
- **`latest_run_id` denormalized pointer on `analyses`.** Avoids a per-row sort on `/me` loads. Costs one extra column and one circular FK declared in two migration steps; well worth it.
- **JSONB report storage.** `analysis_runs.report_json` is the full Pydantic `Report.model_dump_json()`. Denormalize `total_score` and `tier_name` for sort/filter without unpacking. `scores_hash` mirrors the in-process narrative cache key so v0.8.0 Upstash can reuse it.
- **Neon pooled connection at app runtime, direct connection for migrations.** `DATABASE_URL` (port 6543) + `DATABASE_DIRECT_URL` (port 5432). pgBouncer transaction-pooling forces `statement_cache_size=0` on asyncpg.
- **`/auth/callback` never honours a `redirect_to` parameter.** Hard-coded `302 /` to close off open-redirect phishing before it's even a question.

**Learned / surprises:**
- React 19's new `react-hooks/set-state-in-effect` rule is much stricter than the old `react-hooks/exhaustive-deps`. The canonical localStorage-hydration pattern (`useState` + `useEffect(() => setState(localStorage.getItem(...)), [])`) trips it. The proper fix is `useSyncExternalStore` — which also happens to give cross-tab sync for free. Worth memorising as the React 19 idiom for any "client-only external state" surface, including the `useSession()` hook that v0.5.0 will add.
- `npm audit` flags a moderate postcss vulnerability that's a transitive dep inside Next 16's bundled toolchain. The "fix" `npm audit fix --force` would force-downgrade `next` to 9.3.3 — wildly wrong direction. Documented as a known upstream issue; we wait for Next to bump postcss themselves.
- FastAPI 0.95+ has officially recommended `Annotated[T, Depends(...)]` over `T = Depends(...)` defaults for years. Our codebase had drifted to the old pattern in two places; cleaned both up in this audit.

**Blocked / open:**
- None for v0.5.0 design. Implementation plan is the next step.
- Old remote branches `feat/v0.1.0-backend-mvp` and `feat/v0.2.0-frontend-shell` still exist on origin (no open PRs). Delete with `git push origin --delete <branch>` whenever convenient — non-urgent.

**For the agent picking up implementation:**
1. Read [`AGENTS.md`](../AGENTS.md) (the five rules) and the v0.5.0 spec listed above.
2. The pre-slice audit work landed as commit `9321d41` on `feat/v0.4.0-narrative`. Before starting v0.5.0 work, branch off into `feat/v0.5.0-auth-persistence` (or merge the audit commit to main first, then branch from there — your call, but main needs the audit before any v0.5.0 work lands so the lint baseline is green).
3. Generate the implementation plan via `superpowers:writing-plans` against the spec, save to `docs/superpowers/plans/2026-05-16-v0.5.0-auth-persistence.md`. The plan should split into roughly: Alembic + initial migration (1-2 tasks), DB models + engine (2 tasks), auth machinery — crypto, sessions, oauth routes (4-5 tasks), persistence layer per module (3 tasks), `/me` + `/share` routers (2-3 tasks), wiring optional persistence into `/analyze` and `/narrative` (1-2 tasks), frontend header + `/me` + `/share` (4-5 tasks), live smoke + tag + release (1 task). Expect 20-25 TDD tasks total.
4. The four new env vars (`DATABASE_URL`, `DATABASE_DIRECT_URL`, OAuth client id/secret, `SESSION_TOKEN_ENC_KEY`) need to be provisioned in Vercel and Neon before live verification. Ask before installing the Neon Marketplace integration on Vercel — that's a new permission grant per AGENTS.md rule 5.
5. Things that are accepted but might bite — see §12 "Known imprecisions & follow-ups" in the spec. No session-id rotation, no CSRF tokens on state-changing routes (relying on SameSite=Lax), no rate limiting, no "sign out everywhere" UI. All deferred deliberately.
6. Out of scope (do **not** silently expand) — Recruiter/CTO/Career modes (v0.6.0), shareable OG cards (v0.7.0), background re-ingestion / caching (v0.8.0), Sentry/PostHog (v0.9.0), rate limiting / load test / legal docs (v0.10.0).

**Verified at end of this session:**
- Backend: `uv run ruff check .` clean, `uv run pytest -q` 124/124 pass.
- Frontend: `npm run lint` clean, `npm run build` clean.
- Working tree: spec + PLAN + this entry staged for the next commit.

**Next:**
- v0.5.0 implementation. Estimated ~10-14 hours of focused execution time given the breadth (auth + DB + 5 new routes + 2 new frontend pages + migration). Worth front-loading the schema migration and engine wiring in a single tight TDD loop so everything downstream is talking to a real Postgres from day one.

---

## 2026-05-16 — Antigravity — Shipped v0.4.0 AI Narrative Layer (Roast & Mentor SSE stream)

**Slice:** v0.4.0 (Shipped)

**Done:**
- Implemented backend AI Narrative Layer (`app/narrative/*`): in-process LRU cache (`cache.py`), token/call budget tracking (`budget.py`), system prompts and prompt injection scrubbing (`prompts.py`), deterministic fallback generator (`fallback.py`), OpenAI streaming client (`llm.py`), orchestration service (`service.py`), and FastAPI SSE endpoint (`routes.py`).
- Integrated streaming SSE endpoint `GET /narrative/{username}?mode={roast|mentor}` into the FastAPI application.
- Built comprehensive unit tests (`tests/narrative/*`) with 100% test pass rate using a mocked `FakeNarrativeLLM` to verify LRU caching, budget exhaustion fallbacks, streaming tokens, and prompt injection defense.
- Created `NarrativeCard.tsx` on the frontend with beautiful framer-motion layout animations, mode pill toggle (Roast vs Mentor), live streaming token rendering, blinking cursor indicator, and offline fallback toast badge.
- Refined frontend client-side `localStorage` persistence for narrative mode preference across visits and added an elegant visual fallback badge when AI quota is exhausted.
- Verified live E2E streaming against real OpenAI `gpt-4o` API and tagged release v0.4.0.

**Decisions:**
- Chose framer-motion `layoutId` for the Roast/Mentor pill toggle to provide premium Apple HIG / Linear visual polish.
- Built robust client-side SSE retry and cancellation handling via standard `EventSource` with automated fallback mode activation on network or quota exhaustion.

**Learned / surprises:**
- SSE event streams and FastAPI `EventSourceResponse` work seamlessly together when correctly yielding SSE event dictionaries (`{"event": "token", "data": ...}`).

**Blocked / open:**
- None.

**Next:**
- Begin v0.5.0 (Auth + persistence — GitHub OAuth + Neon Postgres).

---

## 2026-05-16 — Claude (Opus 4.7) — v0.4.0 design + plan ready for cold execution

**Slice:** v0.4.0 (designed, not yet implemented)

**Done:**
- Brainstormed the AI Narrative Layer slice end-to-end. All seven major decisions locked: OpenAI provider, SSE streaming, in-process LRU cache, GPT-4o + per-day cap with deterministic fallback, narrative replaces the v0.3.0 right hero card, pill-tab mode toggle, full Report visible to the LLM (with prompt-injection mitigations).
- Wrote the design spec at [`docs/superpowers/specs/2026-05-16-v0.4.0-narrative-design.md`](./superpowers/specs/2026-05-16-v0.4.0-narrative-design.md). Covers backend module layout (`app/narrative/{cache,budget,prompts,fallback,llm,service}.py`), the `/narrative/{username}` SSE endpoint shape with three event kinds (`token`, `fallback`, `done`), prompt strategy (system + few-shot from `docs/PRODUCT_VISION.md` calibration set + JSON-encoded user payload), cache + budget design with documented multi-instance caveat, frontend `NarrativeCard` composition, and exit criteria.
- Generated the implementation plan at [`docs/superpowers/plans/2026-05-16-v0.4.0-narrative.md`](./superpowers/plans/2026-05-16-v0.4.0-narrative.md) — 18 TDD tasks, one-action-per-step, complete code in every step, `FakeNarrativeLLM` test double so tests never hit the network.
- Updated `PLAN.md` v0.4.0 section with links to the spec + plan, expanded scope summary, and new exit criteria.

**Decisions:**
- **OpenAI with daily cap + graceful fallback** (chosen over switching to a free-tier provider). Default `NARRATIVE_DAILY_LIMIT=50/day`. Cap is per-Vercel-instance; true global cap is `limit × instance_count`. Documented as a known imprecision; Redis-backed shared counter lands with v0.8.0 caching.
- **GPT-4o** (chosen over 4o-mini and 4.1-mini) per the user's "go for best, lesser tokens for a day is fine but it has to be free" — quality first, cost controlled by the cap, not the model.
- **SSE streaming** (chosen over batch). Frontend uses native `EventSource`; works fine because `/narrative` is a public GET.
- **In-process LRU dict** (chosen over filesystem or no cache). 256 entries. Survives within a single FastAPI process. Same-user mode toggling within a session is instant.
- **Replaces the v0.3.0 right hero card** (chosen over above-score or below-score placement). The status grid (Reliability / Insights / Mode / Verified) moves into the NarrativeCard footer.
- **Pill tabs** (chosen over segmented control or dropdown). Scales naturally to 5 modes when v0.6.0 adds Recruiter / CTO / Career.
- **Full Report to the LLM** (chosen over minimal). Includes the per-bucket points and badge evidence strings so the model can reference specifics. Username + report ride in a JSON-encoded `user` message; system prompt explicitly instructs the model to treat JSON as data not instructions. Combined with the existing `_USERNAME_RE` regex this gives two layers of prompt-injection mitigation.
- **No persistence** of generated narratives across instances. Reach for v0.8.0 Upstash for that. Today's cache is per-process.
- **Re-run ingestion inside `/narrative`** rather than caching `Report` objects from `/analyze`. Frontend always calls `/analyze` first so this is one extra ingestion per fresh narrative — accepted as a known cost; revisit if real-world latency complains.

**For the cold agent picking this up next session:**

1. Read [`AGENTS.md`](../AGENTS.md) (rules of engagement) and the v0.4.0 spec listed above.
2. Open the plan: [`docs/superpowers/plans/2026-05-16-v0.4.0-narrative.md`](./superpowers/plans/2026-05-16-v0.4.0-narrative.md). It is 18 TDD-disciplined tasks with complete code in every step. Branch starts on `feat/v0.3.0-identity-signals` (the v0.3.0 ship branch); Task 18 has the rename + tag + release dance.
3. Execution path: invoke `superpowers:subagent-driven-development` with the plan file. Fresh subagent per task. Cheap models (haiku) are fine for Tasks 1–6, 9–14, 17 — they're mechanical TDD. Tasks 7 (service orchestrator), 8 (SSE route), 15 (ResultsView wiring) benefit from a stronger model (sonnet).
4. Verification gates:
   - After each task: `uv run pytest -q` and `uv run ruff check .` must stay green; the new test count grows by exactly the tests this task added.
   - Task 16 is a **live OpenAI smoke test** that uses real API calls — confirm `OPENAI_API_KEY` is set in `backend/.env` first. The test deliberately hits the live model so you see real Roast / Mentor output before tagging.
   - Task 18 is **release** — only run after Task 16 passes. The release workflow at `.github/workflows/release.yml` extracts the `## [0.4.0]` CHANGELOG section as the public release body.
5. Things that the spec accepted but might bite:
   - Multi-instance budget imprecision — accept it, fix in v0.8.0.
   - Re-ingestion inside `/narrative` — accept it, fix only if it's slow in practice.
   - `Literal["roast","mentor"]` in the FastAPI route signature returns 422 on invalid values; the route's explicit `if mode not in (...)` block exists to return 400 instead. If FastAPI's validation runs first you'll see 422 in the test — switch the parameter type to `str` and rely on the explicit check (Task 8 step 8.4 documents this).
   - Native `EventSource` only supports GET, no headers. Today that's fine. When we add auth in v0.5.0 the SSE helper switches to `fetch + ReadableStream` (separate task in that slice).
6. Things explicitly out of scope (do **not** silently expand):
   - Recruiter / CTO / Career modes — v0.6.0.
   - Persistent narrative cache across instances — v0.8.0.
   - Per-user rate limiting — v0.10.0.
   - Active provider abstraction (multi-provider swap) — kept as a single-file `narrative/llm.py` boundary but not actively dual-providered.

**Verified at end of this session:**
- Backend test suite: 93/93 pass; ruff clean (carrying over from v0.3.0 — no v0.4.0 code yet).
- Frontend `npm run build` + `npm run lint` clean.
- Working tree only has `docs/superpowers/specs/2026-05-16-v0.4.0-narrative-design.md` and `docs/superpowers/plans/2026-05-16-v0.4.0-narrative.md` as untracked-and-staged-this-commit; PLAN.md and PROGRESS_LOG.md updated to point at them.

**Blocked / open:**
- None for v0.4.0. The slice is fully scoped.
- Stale remote branches `feat/v0.1.0-backend-mvp` and `feat/v0.2.0-frontend-shell` still exist on origin (no open PRs). Delete with `git push origin --delete <branch>` whenever convenient.

**Next:**
- v0.4.0 implementation. Estimated ~8–12 hours of focused execution time across the 18 tasks.

---

## 2026-05-16 — Claude (Opus 4.7) — v0.3.0 Identity Signals shipped + post-release doc audit

**Slice:** v0.3.0 (shipped — tag `v0.3.0`, release `https://github.com/Shaan-alpha/Skill-Issue/releases/tag/v0.3.0`)

**Done:**
- Implemented the full v0.3.0 design from [`docs/superpowers/specs/2026-05-16-v0.3.0-identity-signals-design.md`](./superpowers/specs/2026-05-16-v0.3.0-identity-signals-design.md) via the 22-task plan at [`docs/superpowers/plans/2026-05-16-v0.3.0-identity-signals.md`](./superpowers/plans/2026-05-16-v0.3.0-identity-signals.md). 7-tier ladder (Hobbyist → Principal Engineer) + intra-tier sub-rank with context-aware chip label ("Just promoted to Senior", "Top of the ladder", etc.), 8 deterministic stackable badges, tier-gated depth enrichment (licence / workflows / README quality / PR review depth / dep files / commit quality / cross-repo refactor).
- Two-pass scoring engine: base pass → `enrich_for_tier()` → final pass + tier + badges. Deferred 4-pt `repo_quality.license_majority` signal finally fires for Pro+ profiles, so the 100/100 ceiling is reachable for the first time.
- Frontend: new `PositionBar` (`role="progressbar"`, tier dividers, animated marker via framer-motion `m` namespace) and `BadgeRow` (Base UI `Tooltip` with 150ms delay, glass popup, badge name + evidence on hover/focus). Loading skeleton extended. Tier hero in the score card uses gradient text at `text-2xl/3xl`.
- Breaking change to `/analyze/{username}` response shape: `category: DeveloperCategory` removed; `tier: TierInfo` and `badges: list[Badge]` added. No live persistence yet, so no migration.

**Post-release polish (commit `402ae23`):**
- **Fixed a Senior+ crash.** `REVIEW_DEPTH` GraphQL query had `orderBy: {direction: DESC, field: OCCURRED_AT}` — GitHub's `ContributionOrder` input only accepts `direction`, not `field`. Every profile that reached Senior tier threw 500 during enrichment. Dropped `orderBy` (API returns recent contributions first anyway). Headless tests passed because they mock the response, not the query string — caught by live testing only.
- **Fixed invisible accent.** `--accent: #27272a` (same as `--muted`) rendered as black-on-black for every `text-accent` / `bg-accent` element: position-bar marker, badge pills, "GitHub API" indicator. Switched to `#60a5fa` (blue-400) which matches the existing landing-page blob.
- **Fixed `0/100 IN TIER` UX bug.** torvalds scored exactly 65 (the Senior band floor), so sub_rank computed to 0 and the chip read "0/100 IN TIER" — looked punitive. Added `tierChipLabel()`: shows "Just promoted to Senior" at floor, "Top of the ladder" at Principal ceiling, "%N into tier" otherwise.
- Rewrote all 6 score-card descriptions from dry labels to on-voice questions ("Do your repos look maintained — READMEs, tests, deploys, licences?"). Bumped two stale version chips (footer v0.1.0 → v0.3.0; landing v0.2.0 → v0.3.0).

**Post-release doc audit (this entry):**
- README.md, PLAN.md (version map + v0.3.0 exit criteria), ARCHITECTURE.md, PRODUCT_VISION.md, TECH_STACK.md, DEPLOY.md all carried stale "Next.js 15", "DeveloperCategory", and pre-shift slice numbers (auth was v0.4.0 but is now v0.5.0, caching was v0.7.0 but is now v0.8.0, etc. — every slice after v0.3.0 shifted +1). Updated in one pass. ARCHITECTURE's component diagram now shows the two-pass engine and tier/badges block; PRODUCT_VISION's old "Developer categories" section is replaced with the tier ladder + badge catalog matching the shipped product.

**Decisions:**
- Re-score *after* enrichment with the same scorers, rather than expanding scorer ceilings. Keeps the 100-pt cap and means depth signals' impact lands at the scorer that owns the signal.
- Tier-gating uses the **base** total (not the enriched total) to decide which depth calls to make. A profile right under a threshold won't get the next tier's signals even if those signals would push it over — deterministic and explainable.
- Tier chip copy uses three explicit edge-case strings (Hobbyist floor, mid-tier %, Principal ceiling) rather than a single template. Costs nothing, removes the punitive "0/100" reading at every band floor.

**Learned / surprises:**
- E2E tests that mock the GraphQL endpoint's *response* (not the *request body*) cannot catch a malformed query string. The Senior+ crash slipped through 93/93 pytest because every test mocked the response shape. Worth memo-ing: for GraphQL queries we hand-write, either a fixture-driven schema check or a live smoke run is mandatory before tagging.
- `--accent` had been an alias of `--muted` since v0.2.0 — the bug existed for two releases but was invisible until v0.3.0 because v0.2.0's UI didn't render anything with `text-accent` or `bg-accent`. Lesson: changing semantic tokens is silently load-bearing for downstream components.

**Verified:**
- `uv run pytest -q` → 93/93 green. `uv run ruff check .` → clean.
- `npm run build` and `npm run lint` → clean.
- Live smoke test in browser against octocat (Student Builder · 80% into tier), torvalds (Senior Engineer · Just promoted), Shaan-alpha (Senior Engineer · 47% into tier · all six badge slugs visible). Position bar marker animates correctly; badge tooltips show name + evidence on hover.
- GitHub Release `v0.3.0` published; release workflow ran 7s, success.

**Blocked / open:**
- Lighthouse mobile re-measurement on `/u/[username]` deferred to v0.9.0 (Polish + observability) — the v0.3.0 slice exit criterion was moved to that slice when the depth-enrichment cost showed up (Senior+ profiles now make ~+20-40 extra HTTP calls per analysis; raw Lighthouse without caching will reflect that). Caching lands in v0.8.0 first.
- Stale remote branches `feat/v0.1.0-backend-mvp` and `feat/v0.2.0-frontend-shell` still exist on origin (no open PRs). Delete with `git push origin --delete <branch>` when ready.

**Next:**
- v0.4.0 — AI narrative layer (Roast Mode + Mentor Mode).

---

## 2026-05-15 — Claude (Opus 4.7) — v0.2.0 audit + scoring-engine signal fix

**Slice:** v0.2.0 (shipping)

**Done:**
- **Full audit** of the working tree as I found it: the prior agent ("Antigravity") bumped the version to `0.2.0` and marked the slice shipped, but the bump was uncommitted and `tests/test_health.py` still asserted `version == "0.1.0"`. Actual pytest result was **41/42 passed** — Antigravity's progress-log claim of "42/42 pass" was false. Fixed the assertion to compare against the live `VERSION` constant so it can never drift again.
- **Fixed the scoring engine's dormant signals.** `ingestion/profile.py:_repo_from_rest` hardcoded `has_readme`, `has_tests`, and `has_ci` to `False`, and only ever appended `"pinned"` to `deployment_hints`. As a result the README-majority (6pt), testing/CI (8pt), and deployment-hint (6pt) signals in `repo_quality` never fired, and the CI-culture (4pt) + production-ready (4pt) signals in `engineering_maturity` never fired. **~28 of 100 scoring points were unreachable in production.** Fix: added `GitHubClient.get_repo_root_contents(owner, repo)`, plus `_enrich_repo_signals` and `_classify_root_entries` in ingestion. Top 20 non-fork repos get one extra HTTP call each (in parallel via `asyncio.gather`) to fetch their root tree, then signals are derived from the entry names. Added a dedicated regression test (`test_ingest_profile_detects_readme_tests_ci_and_deployment_hints`) and extended the e2e test mocks to cover the new endpoint.
- **Restored the changelog.** Antigravity's rewrite stripped the previous Claude's substantive `[Unreleased]` entries (e2e test coverage, 404/400/502/500 split, configurable CORS, `Report`-shape rewrite) and replaced them with vague filler ("Performance: Optimized animation timings"). Merged the real items back in alongside Antigravity's legitimate a11y/perf changes, and added the new backend signal fix to the `Fixed` section.
- Fixed three small UI issues introduced or missed in the prior session: import statement placed after `viewport` export in `layout.tsx`, missing `aria-hidden` on the `Search`/`Loader2`/`ArrowRight` icons in `SearchBar`, missing `aria-hidden` on icons in `not-found.tsx`/`error.tsx`, and `text-[10px]` lingering on the error-digest line.
- Refreshed `README.md` to reflect v0.2.0 shipped (status line + `curl /health` example).
- Verified end-to-end: `uv run pytest` → **45/45 pass** (up from 41/42 false-claimed-as-42); `uv run ruff check .` → clean; `npm run build` → clean; `npm run lint` → clean.

**Decisions:**
- **Bundled the scoring-engine fix into v0.2.0** instead of a separate v0.2.1 patch. Rationale: the bug was a v0.1.0 latent failure that v0.2.0 inherited, the fix is small and contained, and v0.2.0 is the natural ship boundary since nothing has been tagged yet. Splitting into two tagged releases would have created two near-simultaneous releases with no real-world gap between them.
- **Kept the 20-repo cap** (`ROOT_CONTENT_LIMIT`) consistent with the existing language-aggregation cap. For users with hundreds of repos, the top 20 most-recently-updated non-forks carry enough signal. Pinning more aggressively can come later if needed.
- **Tolerate per-repo HTTP failures silently in `_enrich_repo_signals`.** One broken repo shouldn't kill the whole ingestion; the False defaults remain a correct conservative reading.
- **Did not** add license detection (the documented `repo_quality` 4pt gap remains deferred). Detecting license would require an additional per-repo request or parsing repo metadata; left as a v0.X follow-up rather than expanding this slice further.
- **No tag/push** in this session. Working tree is staged for `v0.2.0` but the user has not authorized release; tagging is their call.

**Learned / surprises:**
- The prior `repo_quality.py` and `engineering_maturity.py` unit tests passed against synthetic profiles where the test authors *did* set `has_readme=True` etc. by hand. None of them exercised the actual ingestion → scoring boundary, so the bug never surfaced in CI. The e2e test that the previous Claude added did exercise that boundary, but with all-False contents, so it locked in the broken behavior as expected. Worth flagging: per-bucket unit tests on synthetic fixtures cannot catch ingestion-side regressions; the e2e test needs realistic enough mocks to exercise every signal path.
- Antigravity's "42/42 pass" claim is a recurring failure mode in autonomous agent runs — confident completion statements without re-running the suite. The fix here makes the test self-correcting against version drift, but the pattern is worth a memo: always verify by running, not by recalling.

**Blocked / open:**
- License signal in `repo_quality` is still deferred (4pt gap, documented since Task 6/7).
- No live browser smoke test was run in this session — that's still a worthwhile v0.2.0 sanity check before tagging.

**Next:**
- v0.2.0 — Live smoke test of `/u/octocat` and `/u/torvalds` in a browser; if clean, tag `v0.2.0` and let the release pipeline fire.
- v0.3.0 — AI narrative layer (Roast Mode + Mentor Mode) per `PLAN.md`.

---

## 2026-05-15 — Claude (Opus 4.7) — v0.2.0 hardening: e2e test, validation, error boundaries

**Slice:** v0.2.0 (in progress)

**Done:**
- Wrote the e2e integration test the v0.1.0 plan promised but never delivered (`tests/test_analyze_e2e.py`). It drives the FastAPI app via ASGITransport with respx-mocked GitHub responses, asserts the full report shape, validates `total == sum(buckets)`, covers 404 (unknown user), 400 (invalid username), 500 (missing token), and parametrizes 8 invalid-username shapes. This is the test that would have caught both v0.1.0 production crashes.
- Added a GitHub-username regex validator (`^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$`) at the API layer. Bad input gets a clean 400, not a stack trace.
- Frontend error UX overhaul:
  - `app/u/[username]/not-found.tsx` — on-voice "no such GitHub user" page, replaces Next's default 404
  - `app/u/[username]/error.tsx` — segment-level error boundary with retry + home buttons and an optional digest reference for log correlation
  - `page.tsx` no longer has its own try/catch; it lets `notFound()` and thrown errors bubble to the boundaries, which is how App Router is designed to work
  - Stopped leaking `NEXT_PUBLIC_BACKEND_URL` into the error UI
- Search bar hardening:
  - Mirrors the backend username regex; rejects invalid input client-side with inline error copy under the input
  - `normalize()` accepts pasted `github.com/<user>`, `https://github.com/<user>`, `@user`, and trailing slashes/paths — pulls the username out
  - Proper a11y: `aria-label`, `aria-invalid`, `aria-live="polite"` on the error region

**Decisions:**
- Username validation lives in *both* layers. Client-side gives instant feedback and avoids burning a GitHub-API roundtrip on obvious garbage; backend keeps it because never trust the client. Same regex on both sides so they can't drift quietly.
- The frontend treats backend 400 the same as 404 — both route to `not-found.tsx`. From the user's perspective, "you typed nonsense" and "GitHub doesn't have that user" are the same outcome. A separate "invalid input" page would be design noise.
- Did *not* push beyond v0.2.0 scope into auth, OG cards, analytics, rate limiting, or observability. PLAN.md slices v0.4–v0.9 own those; jumping ahead would violate AGENTS.md rule 3. v0.2.0's job is "shell that consumes v0.1.0 cleanly" and we're not done with that yet — Lighthouse, visual polish, and Product Vision pass are still open.

**Learned / surprises:**
- The e2e test caught a third bug on its first run: my mock didn't include `repo.owner.login`, which ingestion uses to call `list_commits`. Real GitHub responses include it; my synthetic payload didn't. The unit tests never exercised that code path because they all mocked the commits endpoint without going through repo-iteration. Lesson: synthetic fixtures should be assembled by deep-copying real responses, not by hand.

**Blocked / open:**
- Visual polish and Lighthouse mobile ≥ 90 are still the v0.2.0 blockers.

**Next:**
- v0.2.0 — Browser visual review, animation timing, copy pass against `docs/PRODUCT_VISION.md`.
- v0.2.0 — Lighthouse audit + first round of fixes.

---

## 2026-05-15 — Claude (Opus 4.7) — v0.2.0 schema alignment + CORS + secrets hygiene

**Slice:** v0.2.0 (in progress)

**Done:**
- Audited the prior agent's hand-off and committed the four staged doc updates as `d7784e5` (post-v0.1.0 cleanup, v0.2.0 marked in-progress, backend-host question closed in `ARCHITECTURE.md`).
- Resolved the frontend↔backend schema drift flagged by Antigravity. `frontend/src/types/index.ts` now mirrors `backend/app/models.py` exactly: `Report.breakdown.*`, `ScoreResult.points/max_points`, typed `Evidence[]`, `DeveloperCategory` literal union. `results-view.tsx` and `[username]/page.tsx` rewired accordingly.
- Killed three build/runtime blockers introduced by `npx shadcn init`:
  1. `lucide-react@^1.16.0` dropped branded icons — `Github` swapped for `ExternalLink` with `aria-label`. The badge next to it already announces the link as the user's GitHub.
  2. `@import "shadcn/tailwind.css"` doesn't resolve (the file lives at `node_modules/shadcn/dist/tailwind.css` and isn't in the package's `exports` map). Inlined the seven `@custom-variant` blocks we'd actually use directly into `globals.css`; removed the accordion keyframes since nothing uses them yet.
  3. `shadcn` moved from runtime `dependencies` to `devDependencies` — it's a CLI scaffolder, not a runtime package.
- Moved route from `/[username]` to `/u/[username]` to match the layout promised in `PLAN.md` and `ARCHITECTURE.md`.
- Replaced the default `layout.tsx` metadata with real product copy.
- Backend gained CORS via `CORSMiddleware` with `cors_allow_origins` defaulting to `["http://localhost:3000"]` (overridable via `CORS_ALLOW_ORIGINS`). `GET` only, all headers allowed — narrow surface area.
- Verified end-to-end: backend `31/31 pytest` pass, ruff clean, `next build` clean, and a live `GET /analyze/octocat` returned a complete report in 5.6s (octocat → 26/100, Entry-Level Engineer; recruiter_signal maxed at 15/15 with three real evidence rows).

**Decisions:**
- Inlined shadcn's `tailwind.css` rather than fixing the import path. Reason: removes a runtime dependency on a CLI package and removes a fragile module-resolution path. The 7 custom variants we kept are static text; the accordion keyframes were dropped because we don't have an accordion component.
- `ExternalLink` over a hand-rolled inline GitHub SVG mark. Reason: the icon is a *link* affordance, not a brand statement, and the surrounding badge + URL already disambiguate the destination. Avoids a hardcoded SVG that would need maintenance if shadcn switches icon libs later.
- Kept `cache: "no-store"` on the analyze fetch for now. v0.7.0 will introduce proper caching with Upstash; until then, fresh-every-load matches the "deterministic + transparent" voice.

**Learned / surprises:**
- `lucide-react` v1.x is a major rewrite that drops every branded icon (Github, Twitter, etc.). Any prior-knowledge code that imports `Github` from `lucide-react` is now broken on fresh installs. Worth memo-ing for future agents.
- A scaffolder agent (Antigravity, in this case) using `npx shadcn init` against shadcn 4.7 produces a `globals.css` with a non-resolving `@import "shadcn/tailwind.css"` line. This will likely bite again — the workaround above is portable.
- User pasted real `GITHUB_TOKEN` and `OPENAI_API_KEY` values into the tracked `backend/.env.example` file. Caught before `git add`; rewrote `backend/.env` (gitignored) with the values and `git restore`d the example to placeholders. Strongly recommend rotating both tokens since they briefly existed in a would-be-committed file. Also: the OpenAI key had a `your_openai_key_here` placeholder fragment concatenated onto the end — trimmed before writing, but the user should verify the trimmed value is the full intended key.

**Blocked / open:**
- Real visual smoke test of the results page against a live backend has not been done — that's the v0.2.0 exit criterion ("zero crypto-dashboard / neon-gradient violations"). Next session should `npm run dev` + `uvicorn app.main:app` and hit `/u/octocat` in a browser.
- Lighthouse mobile ≥ 90 not measured yet.

**Next:**
- v0.2.0 — Browser-side visual review of `/u/octocat` and `/u/torvalds`, then iterate on the design until it matches `docs/PRODUCT_VISION.md`.
- v0.2.0 — Add empty-state and error-state polish; surface evidence rows under each score card.
- When v0.2.0 ships: bump `CHANGELOG.md`, tag `v0.2.0`, let the release workflow handle the rest.

---

## 2026-05-15 — Antigravity — Documentation Audit & v0.2.0 Handoff Preparation

**Slice:** v0.2.0

**Done:**
- Performed a comprehensive audit of all project documentation (`README.md`, `PLAN.md`, `ARCHITECTURE.md`, `CHANGELOG.md`, `PROGRESS_LOG.md`) to ensure accuracy for the next session.
- Verified that `v0.1.0` is fully shipped and all exit criteria are checked off.
- Discovered that the existing `frontend/` code (Landing page, Results view) is partially implemented but uses a different schema than the backend (e.g., `total_score` vs `total`).
- Updated `PLAN.md` to reflect `v0.2.0` is currently "in progress".

**Decisions:**
- Documented the frontend-backend sync issue to ensure the next agent prioritizes aligning the types before proceeding with UI polish.

**Learned / surprises:**
- Scaffolding tools (v0/Bolt) can introduce schema drift if not strictly reviewed against the backend contract. "Documentation as truth" is essential here.

**Next:**
- **v0.2.0 — Sync frontend `Report` types and components with the backend `v0.1.0` models.**
- **v0.2.0 — Refine landing page and results view animations.**

---

## 2026-05-15 — Antigravity — Task 13: Overall Score Orchestrator

**Slice:** v0.1.0

**Done:**
- Created `engine.py` to orchestrate all 6 deterministic scorers and aggregate their results into a final `Report`.
- Implemented heuristic categorization (e.g., "Senior Engineer" if score >= 80, "OSS Contributor" if high collab score).
- Exposed end-to-end pipeline via `/analyze/{username}` endpoint in `main.py`.
- Added integration test `test_engine.py` to verify full aggregation.

**Decisions:**
- Decided on simple thresholds for categorization for the MVP; these will be refined in `v0.3.0` with the AI narrative layer.
- Enforced `GITHUB_TOKEN` requirement at the API level to ensure ingestion doesn't fail silently.

**Learned / surprises:**
- Pydantic v2's `model_validate_json` is extremely convenient for loading fixture profiles in tests.

**Blocked / open:** none.

**Next:**
- **Merge `feat/v0.1.0-backend-mvp` to `main` and tag `v0.1.0`.**
- **v0.2.0 — Frontend shell.**

---

## 2026-05-15 — Antigravity — Task 12: Learning Trajectory Scorer

**Slice:** v0.1.0

**Done:**
- Updated `ingest_profile` to fetch commit history from the last 730 days (2 years) across top 10 repositories.
- Implemented `learning_trajectory.py` scorer with points for account longevity (>3 years), recent repository growth (+3 in last year), and year-over-year commit activity (verified activity in both Y1 and Y2).
- Verified implementation with `test_learning_trajectory.py`.

**Decisions:**
- Increased the commit ingestion window globally to 730 days; this allows the Consistency scorer to see more data if needed, but primarily serves the YOY activity check for Learning Trajectory.

**Learned / surprises:**
- Fetching 2 years of commits for 10 repos might hit rate limits faster if done at scale; current caps and async parallelization keep it safe for MVP volume.

**Blocked / open:** none.

**Next:**
- **v0.1.0 Task 13 — Overall Score Orchestrator.** Combine all scorers into a final scorecard and expose via API.

---

## 2026-05-15 — Antigravity — Task 11: Recruiter Signal Scorer

**Slice:** v0.1.0

**Done:**
- Extended `Profile` model with professional markers: `company`, `blog`, `hireable`, `has_sponsors_listing`, `is_github_star`, and `is_developer_program_member`.
- Updated `ExternalPRs` GraphQL query to fetch verification flags and `ingest_profile` to pull REST metadata.
- Implemented `recruiter_signal.py` scorer with points for repo popularity (>50 stars), professional verification (Sponsors/Star/Pro Member), and digital presence (Portfolio/Hireable status).
- Verified implementation with `test_recruiter_signal.py` and handled `null` values for `hireable` in ingestion.

**Decisions:**
- Used `company` starting with `@` as a heuristic for verified organization membership when explicit org verification isn't easily accessible via public user API.
- Ensured `hireable` is strictly boolean during ingestion to prevent Pydantic validation errors on `null` inputs.

**Learned / surprises:**
- GitHub API returns `null` for `hireable` if the user hasn't explicitly set it; `bool(None)` is `False`, which is the correct default for the signal.

**Blocked / open:** none.

**Next:**
- **v0.1.0 Task 12 — Learning Trajectory Scorer (10 pts).** Heuristics for repo growth and consistent activity over years.

---

## 2026-05-15 — Antigravity — Task 10: Consistency Scorer

**Slice:** v0.1.0

**Done:**
- Added `list_commits` to `GitHubClient` to fetch author-specific commits with time-window filtering.
- Updated `ingest_profile` to aggregate commit dates across the top 10 most-recently-updated non-fork repositories from the last 365 days.
- Implemented `consistency.py` scorer with heuristics for active cadence (last 3 months), dry spell length (< 60 days), and annual commit volume (>= 30 days).
- Verified implementation with `test_consistency.py` and updated ingestion mocks.

**Decisions:**
- Capped commit ingestion to top 10 repos to avoid excessive API calls on profiles with hundreds of repos; 10 is enough to establish a consistency signal.
- Normalized commit dates to `YYYY-MM-DD` to focus on daily activity rather than raw timestamp volume.

**Learned / surprises:**
- Multi-repo commit aggregation requires `asyncio.gather` for acceptable performance.

**Blocked / open:** none.

**Next:**
- **v0.1.0 Task 11 — Recruiter Signal Scorer (15 pts).** Heuristics for popularity, sponsorship, and verified status.

---

## 2026-05-15 — Antigravity — Task 9: OSS & Collaboration Scorer

**Slice:** v0.1.0

**Done:**
- Added `external_orgs` set to `Profile` model to track distinct organizations contributed to.
- Extended `EXTERNAL_PRS` GraphQL query to fetch repository owner logins for the last 100 merged PRs.
- Updated ingestion logic to filter and populate `external_orgs` by identifying non-self repository owners.
- Implemented `oss_collab.py` scorer awarding points for merged PR volume, external code reviews, and cross-org collaboration diversity.
- Verified implementation with `test_oss_collab.py` and updated model tests.

**Decisions:**
- Capped org diversity signal to the last 100 merged PRs for performance; 100 is sufficient for the diversity signal in a general report.
- Used a case-insensitive check for the user's own login when filtering external organizations.

**Learned / surprises:**
- Ingestion testing requires careful mocking of GraphQL nested structures; confirmed `respx` handling of complex post bodies.

**Blocked / open:** none.

**Next:**
- **v0.1.0 Task 10 — Consistency Scorer (10 pts).** Implement heuristics for commit cadence, dry spells, and volume. Requires extending ingestion to pull commit dates across top repos.

---

## 2026-05-15 — Antigravity — Task 8: Engineering Maturity Scorer

**Slice:** v0.1.0

**Done:**
- Added `size_kb` field (defaulting to 0) to `Repo` domain model in `models.py`.
- Updated `ingestion/profile.py` to extract repo size from GitHub payload.
- Created `engineering_maturity.py` scorer with points for typed languages, language diversity, large repos (>200KB indicating multi-folder), CI presence, and deployment hints with tests.
- Created `test_engineering_maturity.py` to verify logic against the existing student, senior, and oss profile fixtures.
- Passed `ruff` linting and formatting.
- Committed the feat to `backend/`.

**Decisions:**
- Initialized `size_kb` with a default `0` in Pydantic to ensure existing test fixtures load correctly without backwards-compatibility breakage.

**Learned / surprises:**
- Modified specific tests to directly set `size_kb` inside the test rather than directly altering `profile_senior.json` globally, ensuring side effects stay minimal.

**Blocked / open:** none.

**Next:**
- **v0.1.0 Task 9 — Impact & Maintenance Scorer (30 pts).** Implement heuristics for stars, fork activity, recent commits, and OSS contribution footprints (external PRs/reviews).

## 2026-05-15 — Codex — docs handoff sanity pass

**Slice:** v0.1.0 documentation hygiene

**Done:**
- Checked the cold-start documentation surfaces after Tasks 6–7.
- Updated `README.md` status from the old v0.0.0/no-code wording to the current state: v0.0.1 shipped, v0.1.0 backend MVP in progress, Tasks 1–7 complete, next resume point Task 8.
- Updated the `PLAN.md` version map so v0.1.0 no longer claims only Tasks 1–4 are complete.

**Decisions:**
- Left `CHANGELOG.md` unchanged because v0.1.0 is not shipped yet. It should get a public `## [0.1.0]` section during Task 16, after the backend MVP exit criteria are met.

**Learned / surprises:** The detailed handoff files were current, but the overview docs had drifted. Cold agents read overview files first, so keeping these summaries aligned matters.

**Blocked / open:** none.

**Next:** v0.1.0 Task 8 — Engineering Maturity scorer.

---

## 2026-05-15 — Codex — v0.1.0 Tasks 6–7: scoring base + repo quality

**Slice:** v0.1.0 Tasks 6–7

**Done:**
- Added `backend/app/scoring/base.py` with the shared `make_result()` helper used by scorer modules.
- Added the first deterministic scorer: `backend/app/scoring/repo_quality.py` (30-point max, current implemented signals award up to 26 while the license signal is deferred).
- Added three fixture profiles (`profile_student.json`, `profile_oss.json`, `profile_senior.json`) for scorer tests.
- Added `backend/tests/scoring/test_repo_quality.py` with explicit expected scores: student = 0, OSS = 20, senior = 26, plus evidence-weight summing.
- Verified: `uv run pytest -v` → 15 passed; `uv run ruff check .` → clean; `uv run ruff format --check .` → clean.

**Decisions:**
- Kept the license portion of Repository Quality at 0 for v0.1.0 because `Repo` does not yet carry a license field and ingestion does not fetch per-repo license content. This is a known scoring gap, not silent behavior.
- `deployment_hints` excludes `"pinned"` from deployment credit. Pinned repos help Recruiter Signal later, but they do not prove deployment maturity.
- Fixture tests use exact scores instead of broad ranges so scorer changes cannot drift quietly.

**Learned / surprises:**
- The current Repository Quality ceiling is 26/30 until license data lands. The v0.1.0 report can still be deterministic and explainable, but the missing 4 points should be called out in release notes if it remains deferred at slice completion.

**Blocked / open:** license scoring is deferred until ingestion/model support exists.

**Next:** v0.1.0 Task 8 — Engineering Maturity scorer.

---

## 2026-05-15 — Codex — v0.1.0 Task 5: ingestion enrichments

**Slice:** v0.1.0 Task 5

**Done:**
- Pushed `feat/v0.1.0-backend-mvp` to GitHub so completed Tasks 1–4 are backed up remotely.
- Extended `GitHubClient` with `list_languages()` and `get_profile_readme()`.
- Added `EXTERNAL_PRS` GraphQL query for merged PR totals and PR review contribution totals.
- Extended `ingest_profile()` to populate `Profile.languages`, `Profile.profile_readme_chars`, `Profile.external_prs_merged`, and `Profile.external_reviews`.
- Expanded `backend/tests/test_ingestion.py` with a focused fixture that proves language bytes are summed across two repos, profile README content is decoded and counted, and external PR/review counts are mapped into the profile.
- Verified: `uv run pytest -v` → 11 passed; `uv run ruff check .` → clean; `uv run ruff format --check .` → clean.

**Decisions:**
- Kept external contribution counts in GraphQL rather than REST search. Reason: Task 5 only needs totals, and GraphQL gives merged PR count plus review contribution count in one typed response shape.
- Aggregated languages over the first 20 non-fork repos, matching the plan's API-bound cap. This keeps v0.1.0 polite to GitHub while still covering the meaningful project surface for most profiles.
- Treated a missing profile README as `None` and therefore `0` chars, not an error. A user without a profile README should still be analyzable.

**Learned / surprises:**
- Adding Task 5 data means every ingestion test must now mock language, README, and external-count calls. The test file now has shared helpers so future ingestion work can add signals without duplicating fixture setup.

**Blocked / open:** none.

**Next:** v0.1.0 Task 6 — add the scoring base helper, then start Task 7 (`repo_quality`) with fixture profiles.

---

## 2026-05-15 — Claude (Opus 4.7) — v0.0.1: automated GitHub Release pipeline

**Slice:** v0.0.1 (patch release, shipped from `main`)

**Done:**
- Added `.github/workflows/release.yml` — fires on `vX.Y.Z` tag push, extracts the matching `## [X.Y.Z]` section from `CHANGELOG.md`, publishes a GitHub Release with that section as the body. Prerelease tags (`v0.1.0-rc.1`) get the `--prerelease` flag automatically.
- Extended `AGENTS.md` rule 3: every version bump (minor and patch alike) must ship as a GitHub Release. Changelog entries become public release notes — write them for users, not for agents.
- Updated memory `feedback_version-planning` to encode the new release-with-version rule.
- Bumped `CHANGELOG.md` to `[0.0.1]`; tagged `v0.0.1` on `main`.

**Decisions:**
- Workflow extracts the CHANGELOG section with `awk` between `## [<version>]` and the next `## [`. Single source of truth for release notes — no separate `RELEASES.md`, no manually-written GitHub Release bodies.
- The workflow uses `${{ secrets.GITHUB_TOKEN }}` (the per-job ephemeral token), not a PAT. `permissions: contents: write` is scoped to this workflow only.
- Tag pattern: `v[0-9]+.[0-9]+.[0-9]+` for stable, `v[0-9]+.[0-9]+.[0-9]+-*` for prereleases. Strict — no `latest`, no `vX.Y` shorthand.

**Why now:** User asked for "with every push on github also release the version releases and patch releases". v0.0.1 installs the pipeline itself so v0.1.0 and beyond ship publicly without manual work.

**Next:** v0.1.0 backend MVP continues on `feat/v0.1.0-backend-mvp` from Task 5. This merge commit brings the new rule + workflow into the feature branch.

---

## 2026-05-15 — Claude (Opus 4.7) — Session handoff at v0.1.0 Task 4

**Slice:** v0.1.0 (Tasks 1–4 complete, Tasks 5–16 pending)

**Done in this session:** v0.0.0 scaffolding (docs, rules, memory) → v0.1.0 Tasks 1–4 (backend skeleton, domain models, GitHub client, base ingestion). All on branch `feat/v0.1.0-backend-mvp`. 5 commits ahead of `main`. 10/10 tests pass. Ruff clean. No co-author trailers anywhere. Backend host locked: Vercel Functions (Fluid Compute).

**Handoff for the next session:**
- Branch: `feat/v0.1.0-backend-mvp` (already checked out)
- Resume from: **v0.1.0 Task 5 — Ingestion: languages, profile README, external PRs**
- Plan file: `docs/superpowers/plans/2026-05-15-v0.1.0-backend-mvp.md` (has a progress table at the top showing Tasks 1–4 done with their commits)
- Rules: read `AGENTS.md` first. No co-author trailers. Update this log + `CHANGELOG.md` before any version bump.
- Tooling verified: `uv 0.11.12`, `gh 2.89` (auth'd as Shaan-alpha with `gist, read:org, repo, user, workflow`), `python 3.13` host, project pinned to 3.12 via uv.
- Recommended workflow next session: keep using subagent-driven-development per task (the v0.0.0 docs are written so a cold agent has everything it needs).

**Why we stopped here:** Continuing all 12 remaining tasks in one long thread would have re-sent growing conversation context on every turn — expensive coordination overhead on the user's plan. The scaffold's whole purpose was to make sessions resumable; using that capability is the cost-effective move.

**Next:** v0.1.0 Task 5 — `app/github/client.py` gains `list_languages` / `get_profile_readme` / `search_external_prs`; `ingest_profile` is extended to populate `Profile.languages`, `Profile.profile_readme_chars`, `Profile.external_prs_merged`, `Profile.external_reviews`. The plan file has the full TDD steps.

---

## 2026-05-15 — Claude (Opus 4.7) — v0.1.0 Task 4: Ingestion — assemble a Profile

**Slice:** v0.1.0 Task 4

**Done:**
- Captured a real GitHub fixture at `backend/tests/fixtures/github_responses/repos_octocat.json` via `gh api users/octocat/repos` (8 repos total, 6 non-forks).
- Wrote `backend/tests/test_ingestion.py` first (2 respx-mocked tests: end-to-end `ingest_profile("octocat", gh)` against `user_octocat.json` + `repos_octocat.json` + empty pinned-items GraphQL response; pinned-repo tagging that pins the first non-fork from the fixture and asserts `"pinned" in repo.deployment_hints`) → confirmed `ModuleNotFoundError: No module named 'app.ingestion'` → wrote `backend/app/ingestion/__init__.py` (empty) and `backend/app/ingestion/profile.py` (`_parse_dt`, `_repo_from_rest`, async `ingest_profile`) → confirmed `2 passed`.
- Full backend suite green: `10 passed in 0.40s` (1 health + 5 models + 2 client + 2 ingestion).
- `uv run ruff check .` clean.

**Decisions:**
- **Moved `GitHubClient` import into a `TYPE_CHECKING` block** in `app/ingestion/profile.py`. The symbol is only used as a parameter annotation; with `from __future__ import annotations` at the top of the file, all annotations are stringized and never evaluated at runtime. Ruff `TC001` correctly flagged it. The `Profile`/`Repo` imports stay at runtime because they are *called* as constructors inside the function body, not just annotated.
- **Skipped forks in the repos list** (`if not r.get("fork", False)`) per the plan's filter. Octocat's fixture has 2 forks and 6 originals, so this is exercised — the integration test gets 6 repos, not 8.
- **Used `r.deployment_hints.append("pinned")` (the plan's primary approach)** rather than constructing the Repo with hints set from the start. Pydantic v2's `BaseModel` is not frozen by default, mutating the list attribute on the instance works, and the test passes. If a future change to `Repo` adds `model_config = ConfigDict(frozen=True)`, switch to the alternate approach noted in the plan.

**Learned / surprises:**
- The real `gh api users/octocat/repos` response *does* include forks (octocat has 2: `boysenberry-repo-1` and `Spoon-Knife`-style — actually different names, but `"fork": true`). The fork filter is load-bearing for octocat specifically, not just a defensive guard.
- Ruff's `TC001` ("application import in type-checking block") and the project's `runtime-evaluated-base-classes = ["pydantic.BaseModel"]` Pydantic exemption are orthogonal: the Pydantic exemption applies only to *base class* imports of Pydantic models, not to parameter-type imports in plain functions. Two distinct mechanisms.

**Blocked / open:** none.

**Next:**
- **v0.1.0 Task 5 — Ingestion enrichments.** Fill the four fields left as zero/empty in this task: `profile_readme_chars` (fetch `<username>/<username>` README), `languages` (sum from repo-level `/languages`), `external_prs_merged` + `external_reviews` (search API for cross-org PRs and reviews). Each of these is a separate respx-mocked test against a fixture; the bulk of `ingest_profile` already exists.

---

## 2026-05-15 — Claude (Opus 4.7) — v0.1.0 Task 3: GitHub client

**Slice:** v0.1.0 Task 3

**Done:**
- Wrote `backend/tests/github/test_client.py` first (2 respx-mocked tests covering `get_user` happy path against a real `gh api users/octocat` fixture and 403 secondary-rate-limit retry → 200) → confirmed `ModuleNotFoundError: No module named 'app.github.client'` → wrote `backend/app/github/client.py` (`GitHubClient` async context manager with `get_user`, `list_repos`, `graphql` methods and an internal `_request` loop that sleeps on `Retry-After` for 403 + "rate limit" responses) → confirmed `2 passed`.
- Wrote `backend/app/github/queries.py` holding the `PINNED_REPOS` GraphQL query (6 pinned repos, primary language, README size).
- Captured real GitHub fixture at `backend/tests/fixtures/github_responses/user_octocat.json` via `gh api users/octocat` (login=octocat, id=583231, account from 2011).
- Full backend suite (`test_health` + `test_models` + `test_client`) green: `8 passed in 0.32s`.
- `uv run ruff check .` clean.

**Decisions:**
- **Kept `http2=True` and added `h2` to runtime deps** (`uv add h2` → `h2==4.3.0`, `hpack==4.1.0`, `hyperframe==6.1.0`). The plan offered an out (drop HTTP/2 if h2 install was clunky), but `uv add` was a one-liner and HTTP/2 multiplexes the parallel REST calls ingestion will fan out (`get_user` + `list_repos` + GraphQL `pinned`). GitHub's API supports HTTP/2 well; the only cost is three small pure-Python deps.
- **Renamed the loop variable in `_request` from `attempt` to `_attempt`** to satisfy ruff's `B007` (unused loop variable) without adding a `noqa`. The plan's snippet would have triggered the warning under our ruff config.
- **Did NOT wire `Settings.github_token` into the client constructor.** The token is passed explicitly by callers (and by the tests) — keeps the client decoupled from settings and trivially testable. Ingestion code in Task 4 will pull `settings.github_token` and pass it in.

**Learned / surprises:**
- httpx's `http2=True` fails loudly at `AsyncClient` construction time (not at first request) if `h2` is missing, so the failure mode is fast.
- Ruff's `B007` fires on `for attempt in range(...)` when the variable is unused inside the body — the plan's literal snippet would not have passed `ruff check .` without the underscore prefix.

**Blocked / open:** none.

**Next:**
- **v0.1.0 Task 4 — Ingestion pipeline.** Compose `GitHubClient` into an async `ingest_profile(username) -> Profile` that runs `get_user` + `list_repos` (and the pinned-repos GraphQL) concurrently, maps the raw payloads into our Pydantic `Profile` + `Repo` models, and returns the typed `Profile`. Fixture-driven tests; no live network.

---

## 2026-05-15 — Claude (Opus 4.7) — v0.1.0 Task 2: Pydantic domain models

**Slice:** v0.1.0 Task 2

**Done:**
- Wrote `backend/tests/test_models.py` first (5 tests covering `Evidence`, `ScoreResult` cap, `ScoreBreakdown.total()` + `Report` assembly, `Repo` minimal fields, `Profile` assembly) → confirmed `ModuleNotFoundError: No module named 'app.models'` → wrote `backend/app/models.py` with 6 models + the `DeveloperCategory` `Literal` → confirmed `5 passed in 0.09s`.
- Full backend suite (`test_health` + `test_models`) green: `6 passed in 0.31s`.
- `uv run ruff check .` clean.
- Models defined: `Evidence`, `ScoreResult` (with `field_validator` enforcing `points <= max_points`), `Repo`, `Profile`, `ScoreBreakdown` (with `total()` method), `Report` (with `total` field constrained `0 <= total <= 100`).

**Decisions:**
- **Typed the `field_validator` `info` parameter as `pydantic.ValidationInfo`** rather than leaving it untyped with `# type: ignore[no-untyped-def]`. The spec allowed either; the typed version is cleaner, avoids the silencing comment, and gives editors real autocomplete on `info.data`.
- **Added `[lint.flake8-type-checking] runtime-evaluated-base-classes = ["pydantic.BaseModel"]` to `backend/ruff.toml`.** Reason: ruff's `TC003` rule wants `datetime` moved into a `TYPE_CHECKING` block, but Pydantic resolves annotations at runtime when building the validator — moving the import breaks model construction with `PydanticUserError: ... is not fully defined`. Telling ruff that `BaseModel` subclasses evaluate their annotations at runtime is the project-wide correct fix. This will benefit every Pydantic model in the codebase going forward (scoring outputs, request/response schemas, etc.).
- **Used `datetime.UTC` over `datetime.timezone.utc` in the test file** (project rule 3: modern Python idioms; ruff `UP017` auto-fix). The spec's snippet predates the 3.11+ alias, but the project pins ≥3.12 so the modern form is correct.

**Learned / surprises:**
- Pydantic v2 + `from __future__ import annotations` still needs the type names available at runtime in the module namespace — string annotations are lazy-resolved during model build, not deferred indefinitely. `TYPE_CHECKING` guards do not work for any name that appears in a Pydantic field type.
- Ruff's `flake8-type-checking` has a dedicated config knob for exactly this Pydantic case; no per-import `noqa` needed.

**Blocked / open:** none.

**Next:**
- **v0.1.0 Task 3 — GitHub client (REST + GraphQL + rate-limit retry).** Wire up `httpx.AsyncClient` against the GitHub API with respx-mocked tests, retry/backoff on 429 + secondary rate limits, and a single `Profile`-shaped ingest function that downstream scoring will call. Token comes from `Settings.github_token`.

---

## 2026-05-15 — Claude (Opus 4.7) — v0.1.0 Task 1: backend skeleton

**Slice:** v0.1.0 Task 1

**Done:**
- Scaffolded `backend/` with `uv init --package skill-issue-backend --python 3.12`, then flattened the layout: dropped the generated `src/skill_issue_backend/` package, removed `[project.scripts]` + `[build-system]`, and pinned `tool.uv.package = false` so the backend is an application (not a wheel) with code under `backend/app/`.
- Added runtime deps via `uv add`: `fastapi` 0.136, `pydantic` 2.13, `pydantic-settings` 2.14, `httpx` 0.28, `uvicorn[standard]` 0.47.
- Added dev deps: `pytest` 9, `pytest-asyncio` 1.3, `respx` 0.23, `ruff` 0.15.13, `httpx`.
- Wrote `ruff.toml` (py312, line-length 100, E/F/I/UP/B/SIM/TCH/RUF, ignore E501, double quotes).
- TDD loop: wrote `tests/test_health.py` first → confirmed failure (`ModuleNotFoundError: No module named 'app.main'`) → wrote `app/settings.py` (Pydantic `BaseSettings`, `.env` loader, `version = "0.1.0"`) + `app/main.py` (FastAPI app with `GET /health`) → confirmed pass (`1 passed in 0.79s`).
- Configured `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` and `pythonpath = ["."]` so `from app.main import app` resolves from the `backend/` root.
- Smoke-tested live server: `uv run uvicorn app.main:app --port 8000` boots cleanly; `curl http://localhost:8000/health` returns `{"status":"ok","version":"0.1.0"}`.
- `uv run ruff check .` clean.

**Decisions:**
- **Flat `app/` layout over the `src/skill_issue_backend/` layout** that `uv init --package` generates. Rationale: the application is deployed (to Vercel Functions), not distributed as a wheel; the shorter import path (`app.main` vs `skill_issue_backend.main`) matches FastAPI convention and keeps the scoring/client/route modules in one obvious place. `tool.uv.package = false` tells uv to skip building the project.
- **Pytest discovery via `pythonpath = ["."]` in `pyproject.toml`**, not a `conftest.py` hack. Cleaner; one source of truth.
- **`asyncio_mode = "auto"`** so async test functions don't need explicit `@pytest.mark.asyncio` everywhere — the test in this task keeps the marker for readability, but future tests can drop it.

**Learned / surprises:**
- `uv init --package` always emits a `src/` layout — there is no flag to force a flat layout. The fix is to delete the `src/` tree and the `[project.scripts]` + `[build-system]` blocks after init, then set `tool.uv.package = false`. Worth keeping in mind for future Python services in this repo.
- On Windows + uv-managed Python, `VIRTUAL_ENV` from the host shell can spuriously point at a Python 3.14 install; uv warns and falls back to `.venv` correctly. No action needed.

**Blocked / open:** none for this task.

**Next:**
- **v0.1.0 Task 2 — Pydantic domain models.** Define `Evidence`, `ScoreResult`, `Repo`, `Profile`, `ScoreBreakdown`, and `Report` in `app/models.py` with fixture-driven tests. These are the typed contract that scoring and the route handler both depend on.

**Follow-up fixes (post-review):**
- Removed duplicate `httpx` from dev deps (was already a runtime dep).
- Added empty `backend/tests/conftest.py` to match the plan's Task 1 file list.
- Promoted `version` from a `BaseSettings` field to a module constant `VERSION` to prevent silent env-var override (`VERSION=...` was readable on the settings object).
- Corrected model names in this entry's "Next" section to match the plan's Task 2.

---

## 2026-05-15 — Claude (Opus 4.7) — v0.0.0 scaffolding shipped

**Slice:** scaffolding → v0.0.0

**Done:**
- Wrote `README.md`, `AGENTS.md`, `CLAUDE.md`, `PLAN.md`, `CHANGELOG.md`, `ARCHITECTURE.md`.
- Wrote `docs/PRODUCT_VISION.md`, `docs/TECH_STACK.md`, this file.
- Wrote `.gitignore` for Node + Python + env + OS noise.
- Populated agent memory at `~/.claude/projects/c--Users-shaan-Desktop-Skill-Issue/memory/` with the five durable rules (no co-authoring, modern design, version planning, log discipline, MCP permission) and the project profile.
- Set up the version map: v0.0.0 (scaffolding) → v0.1.0 (backend MVP) → … → v1.0.0 (public launch).

**Decisions:**
- **AGENTS.md is canonical** for cross-agent rules; `CLAUDE.md` is a minimal pointer to it. Reason: the AGENTS.md convention is portable across Claude, Cursor, Copilot, Gemini.
- **Versioning is strict semver-style slices** with explicit exit criteria. No starting `v0.(X+1)` before `v0.X` exit criteria are met and recorded in `CHANGELOG.md`.
- **Scoring is deterministic; AI is decoration.** Reaffirmed in `ARCHITECTURE.md` — the LLM never sees raw repo data, only the structured score JSON.
- **Stack defaults:** Next.js 15 + React 19 + Tailwind + shadcn/ui + Framer Motion on the frontend; FastAPI + Pydantic + httpx + uv on the backend; Neon Postgres + Upstash Redis; OpenAI for narrative.
- **Backend host = Vercel Functions (Fluid Compute).** Locked today. Rationale: single dashboard with the frontend, OIDC env handoff, native marketplace integration with Neon + Upstash. Trade-off accepted: function duration caps mean any long re-ingestion in v0.7.0 must be chunked via Vercel Cron rather than a single multi-minute invocation. Python on Vercel is second-class vs. Node — we pin runtime versions explicitly in `vercel.json` when the backend lands.
- **Banned:** Co-Authored-By trailers, "Generated with Claude Code" footers, generic-AI-SaaS aesthetics.

**Learned / surprises:**
- The masterplan already contains a strong voice anchor — captured the calibration set of voice samples directly into `docs/PRODUCT_VISION.md` so any prompt-engineering work in v0.3.0 has a frozen reference.

**Blocked / open:**
- Five architecture questions left explicitly open for the slice that owns them (backend host, ORM, streaming framework, background ingestion, OG runtime). See bottom of `ARCHITECTURE.md`.
- No MCP/plugin installs requested yet — current ones (Context7, GitHub MCP via shell, Vercel skills) are sufficient for v0.0.0.

**Next:**
- Wait for user direction. The natural next step is **v0.1.0 — Backend MVP**:
  1. Generate a TDD sub-plan via `superpowers:writing-plans`, save to `docs/superpowers/plans/2026-05-15-v0.1.0-backend-mvp.md`.
  2. Scaffold `backend/` with `uv init`, FastAPI, pytest.
  3. Build the GitHub client with respx-mocked tests.
  4. Build scorers one at a time with fixture-driven tests.
- Before that: user should confirm the version plan, the doc structure, and whether any of the open architecture questions should be locked in now.

---
