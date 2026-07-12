# Launch readiness (v1.0.0)

The code is launch-ready as of **v0.9.8**. v1.0.0 is the public launch itself — mostly human-gated actions. This checklist organizes them. Bump the version to `1.0.0` only *after* the launch is live and stable (its exit criteria are about real traffic, not code).

## 1. Pre-launch verification

- [ ] **Legal review.** Have a professional review `/privacy` + `/terms` (`frontend/src/app/{privacy,terms}/page.tsx`). They're honest plain-language drafts, **not** legal advice.
- [ ] **Load test.** Run the full warm-`/analyze` 100 RPS test per [`backend/loadtest/README.md`](../backend/loadtest/README.md) (local SRH + Docker). Record max sustainable RPS + p95 in `docs/PROGRESS_LOG.md`.
- [ ] **Security config (verified 2026-05-29, re-confirm before launch):**
  - `COOKIE_SECURE=true` in prod — confirmed via the `si_oauth_state` cookie carrying `Secure`.
  - `CORS_ALLOW_ORIGIN_REGEX` scoped to our origins — confirmed (`evil.example.com` + arbitrary `*.vercel.app` rejected).
  - `INTERNAL_PROXY_SECRET` set on both Vercel services (turns on anonymous `/analyze` IP rate limiting).
  - Security headers live — confirmed via `curl -I` (`X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, CSP report-only). Consider promoting the CSP from report-only to enforcing after tuning against real violation reports.
- [x] **Smoke the live app** (2026-07-12, on skillissue.tech): `/health` `up/up`, sign-in works, an analysis runs, `/me` history works, a `/share/<slug>` link resolves.

## 2. Production domain + SSL — ✅ done 2026-07-12

- [x] Register **skillissue.tech** — redeemed free via the GitHub Student Pack .TECH offer (2026-07-11).
- [x] Vercel → Domains: apex on Production, `www` 307→apex, old `skill-issue-tau.vercel.app` 308→apex. Nameservers delegated to Vercel (`ns1/ns2.vercel-dns.com`); SSL auto-issued.
- [x] Env cutover done: `CORS_ALLOW_ORIGINS`, `OAUTH_REDIRECT_URL` (+ GitHub OAuth App callback), `FRONTEND_BASE_URL`, `NEXT_PUBLIC_SITE_URL`, `NEXT_PUBLIC_BACKEND_URL`. **Lesson:** two envs mis-saved on the first pass (`OAUTH_REDIRECT_URL` → `invalid redirect_uri`; `NEXT_PUBLIC_BACKEND_URL` → sign-in "succeeded" but UI stayed logged out because `/me` fetched the old host without the cookie). Verify env edits by probing the deployed artifact (login `Location` header; grep the JS chunks for the baked host), not by trusting the dashboard.
- [x] OAuth sign-in re-verified end-to-end on skillissue.tech (2026-07-12).
- [x] Sentry sampling envs set (`NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE=0.2`, replay 0.1/1.0, backend `SENTRY_TRACES_SAMPLE_RATE=0.2`).

> **Deploy quirk (recurring):** the dashboard **Redeploy** button fails on this repo (`No Next.js version detected` — multi-service root detection). Apply env changes by pushing a commit (empty is fine). First seen v0.9.x, reconfirmed 2026-07-11.

## 3. Launch day

- [ ] Final deploy on `main`; confirm `/health` version.
- [ ] Launch posts: Hacker News (Show HN), X, Reddit (r/programming), LinkedIn. Lead with a real example report link (e.g. `/u/torvalds`).
- [ ] Watch **Sentry** (errors) + **PostHog** (traffic, web vitals) dashboards.
- [ ] Be available for the first few hours (informal on-call).

## 4. Post-launch

- [ ] Watch for 72 hours of stable traffic (error budget holds, no pool/rate-limit surprises — the v0.9.4 pool knob `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` and Neon connection ceiling ~105 are the levers if needed).
- [ ] Document the informal on-call rotation.
- [ ] Write a launch retro in `docs/PROGRESS_LOG.md`.
- [ ] Bump `CHANGELOG.md` + version literals to **1.0.0**, tag `v1.0.0`, release.

## Beyond v1.0.0

Tracked in [`PLAN.md`](../PLAN.md) "Beyond v1.0": GitLab / LinkedIn / Resume checkers, same deterministic-scoring + narrative architecture.
