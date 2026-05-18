# Changelog

All notable changes to **Skill Issue** are recorded here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every version listed here must correspond to a slice in [`PLAN.md`](./PLAN.md) whose exit criteria have been met.

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
