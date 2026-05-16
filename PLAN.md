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
| **v0.4.0** | AI narrative layer — Roast Mode + Mentor Mode | pending |
| **v0.5.0** | Auth + persistence — GitHub OAuth + Neon Postgres | pending |
| **v0.6.0** | Remaining modes — Recruiter, CTO, Career | pending |
| **v0.7.0** | GitHub Receipts™ — shareable OG cards | pending |
| **v0.8.0** | Caching + performance — Upstash Redis, rate-limit hygiene | pending |
| **v0.9.0** | Polish + observability — analytics, error tracking, perf budget | pending |
| **v0.10.0** | Beta hardening — security review, abuse mitigation, load test | pending |
| **v1.0.0** | Public launch | pending |

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
- [ ] `/narrative/{username}?mode=roast` streams a valid SSE response for all 5 fixture profiles (Hobbyist → Staff).
- [ ] `mode=mentor` produces tonally distinct output from `mode=roast` for the same profile (snapshot diff asserts the prompt diverges; live smoke confirms the output diverges).
- [ ] Toggling modes on `/u/{username}` never changes the displayed score, tier, badges, or position bar.
- [ ] `NARRATIVE_DAILY_LIMIT=0` makes every request hit the fallback path; UI shows the offline badge; rest of the page unaffected.
- [ ] No prompt-injection succeeds for adversarial usernames or report fields (regex + JSON envelope verified by tests).
- [ ] Second call with same `(username, scores_hash, mode)` returns in < 200ms, no LLM call (LRU cache hit).
- [ ] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.4.0`.

---

## v0.5.0 — Auth + persistence

**Goal:** Users sign in with GitHub. Analyses are stored. Repeat visits are fast.

**Slice scope:**
- GitHub OAuth (server-side flow, httpOnly cookies)
- Neon Postgres schema: `users`, `analyses`, `analysis_runs`, `narratives`
- Migration tooling (`alembic` or `drizzle` depending on backend boundary — decide and log)
- Authenticated users get higher rate limits and saved analyses
- `/me` page with history
- Privacy default: an analysis is private unless explicitly shared

**Exit criteria:**
- [ ] Sign-in flow works in preview and prod
- [ ] Analyses persist and are retrievable by user
- [ ] Schema migrations are reversible and tested
- [ ] No raw GitHub tokens stored in the DB (only refresh-required flow or short-lived session)
- [ ] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.5.0`

---

## v0.6.0 — Remaining analysis modes

**Goal:** Recruiter, CTO, and Career modes shipped behind the same mode toggle.

**Slice scope:**
- Three new prompt templates with their own regression fixtures
- Mode-specific score emphasis: Recruiter weights Recruiter Signal + Repo Quality; CTO weights Engineering Maturity + Consistency; Career weights Learning Trajectory + OSS/Collab
- Per-mode "headline insight" computed deterministically and passed to the LLM as a constraint

**Exit criteria:**
- [ ] All five modes (Roast, Mentor, Recruiter, CTO, Career) live and on-voice
- [ ] Mode-specific emphasis is visible in the rendered narrative
- [ ] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.6.0`

---

## v0.7.0 — GitHub Receipts™

**Goal:** Every analysis produces a shareable scorecard image suitable for LinkedIn, X, and OG previews.

**Slice scope:**
- Next.js `@vercel/og` route generating a 1200×630 card
- Variants: dark, light, "minimal score-only," "full breakdown"
- Twitter/X meta tags, LinkedIn meta tags, Open Graph
- `/u/[username]/card` route with a one-click copy/download
- Brand mark + subtle background, never gradient soup

**Exit criteria:**
- [ ] OG card renders in under 800ms on Vercel
- [ ] Cards pass real-world preview tests on X and LinkedIn
- [ ] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.7.0`

---

## v0.8.0 — Caching + performance

**Goal:** Repeat analyses are free and fast.

**Slice scope:**
- Upstash Redis cache for: GitHub API responses (TTL per endpoint), score reports, LLM narratives
- Background re-ingestion for users with saved analyses (cron)
- Coalescing of concurrent requests for the same username
- Frontend perf budget: TTI ≤ 2.5s on 3G, CLS ≤ 0.1, LCP ≤ 2.5s

**Exit criteria:**
- [ ] p95 latency for a cached analysis ≤ 200ms end-to-end
- [ ] Lighthouse mobile performance ≥ 95 on `/u/[username]`
- [ ] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.8.0`

---

## v0.9.0 — Polish + observability

**Goal:** The product feels finished. We can see what users do and what breaks.

**Slice scope:**
- Sentry (frontend + backend)
- PostHog or Plausible analytics
- Structured logging on every backend route
- 404 / 500 / rate-limit pages with on-voice copy
- Accessibility audit (axe): zero criticals
- Empty states and skeleton loaders everywhere

**Exit criteria:**
- [ ] Error budget defined; dashboards live
- [ ] Axe critical issues = 0
- [ ] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.9.0`

---

## v0.10.0 — Beta hardening

**Goal:** Public-ready security and abuse posture.

**Slice scope:**
- Rate limiting per IP + per authenticated user
- Abuse heuristics: reject usernames with suspicious patterns, throttle scrapers
- Security review (manual + run `/security-review`)
- Load test to 100 RPS sustained
- Privacy policy + terms

**Exit criteria:**
- [ ] No high or critical issues from `/security-review`
- [ ] Load test passes target without errors
- [ ] Legal docs live and linked from footer
- [ ] `CHANGELOG.md` + `docs/PROGRESS_LOG.md` updated; version `0.10.0`

---

## v1.0.0 — Public launch

**Goal:** Ship it.

**Slice scope:**
- Production domain + SSL
- Launch post (HN, X, LinkedIn, Reddit r/programming)
- Marketing landing variant with social proof / testimonials
- Public roadmap moved to GitHub Issues / Projects

**Exit criteria:**
- [ ] Production traffic stable for 72 hours
- [ ] On-call rotation documented
- [ ] Post-launch retro in `docs/PROGRESS_LOG.md`
- [ ] `CHANGELOG.md` bumped to `1.0.0`

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

- **Team Intelligence** — analyze an org's engineering identity
- **OSS Reputation Score** — public leaderboard for OSS contributors
- **Career Timeline** — animated history of a developer's growth
- **Hiring Mode** — recruiter dashboard with shortlists
- **Skill Graphs** — visualize stack expertise as a graph
- **Engineering Evolution Tracking** — month-over-month deltas

---

## Process notes for agents

1. **Pick a slice from the current version.** Do not jump ahead.
2. **Generate a TDD sub-plan** for the slice using the `superpowers:writing-plans` skill. Save to `docs/superpowers/plans/`.
3. **Implement task by task,** keeping commits small. No co-authoring.
4. **Update logs** as you go (`CHANGELOG.md` + `docs/PROGRESS_LOG.md`).
5. **Verify exit criteria** before bumping the version.
6. **Ask before** any new MCP/plugin permission or external account.
