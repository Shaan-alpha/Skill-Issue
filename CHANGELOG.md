# Changelog

All notable changes to **Skill Issue** are recorded here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every version listed here must correspond to a slice in [`PLAN.md`](./PLAN.md) whose exit criteria have been met.

---

## [Unreleased]

> Post-v0.8.0 housekeeping. Will roll into the `[0.8.1]` section when that slice ships, following the same convention used for pre-v0.7.1 / pre-v0.5.0 audits.

### Security
- **`happy-dom` `^15` → `^20`** to clear GHSA-37j7-fg3j-429f (VM Context Escape can lead to Remote Code Execution). Dev-only test environment — we never feed untrusted HTML through it, so real blast radius is nil — but AGENTS.md rule 1 ("modern tools always") + the critical severity made the bump cheap. 34/34 vitest still passes. Remaining `npm audit` is two moderate advisories inside Next 16.2.6's transitive `postcss`, cleared when Next 16.3 ships.

### Changed
- **`ruff format` pass on 51 backend files.** `ruff check` was being enforced post-v0.8.0 but `ruff format` had silently drifted across the v0.5.0 → v0.8.0 commits. Pure whitespace/style normalization, no behavior change; the 221 non-DB-fixture tests still pass at exactly 221. `docs/TECH_STACK.md` now notes that `ruff check` and `ruff format` are independent passes.
- **Backend dep refresh** (`uv lock --upgrade`, all within existing `>=` constraints): ruff 0.15.13 → 0.15.14, starlette 1.0.0 → 1.0.1, openai 2.37 → 2.38, joserfc 1.6.5 → 1.6.7, jiter 0.14 → 0.15, click 8.3.3 → 8.4.1, certifi 2026.4.22 → 2026.5.20, greenlet 3.5.0 → 3.5.1, idna 3.15 → 3.16, watchfiles 1.1.1 → 1.2.0.
- **Frontend dep refresh** (`npm update`, within `^` ranges — `package.json` unchanged): @base-ui/react 1.4.1 → 1.5.0, framer-motion 12.38 → 12.40, shadcn 4.7 → 4.8, @types/react 19.2.14 → 19.2.15. Side effect: `qs` transitive DoS advisory cleared.

### Notes
- v0.8.1 design spec landed at [`docs/superpowers/specs/2026-05-22-v0.8.1-cron-reingest-design.md`](./docs/superpowers/specs/2026-05-22-v0.8.1-cron-reingest-design.md). Implementation gated on `CRON_SECRET` provisioning (user action — AGENTS.md rule 5).

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
