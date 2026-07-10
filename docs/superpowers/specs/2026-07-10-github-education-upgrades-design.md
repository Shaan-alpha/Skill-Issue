# GitHub Education Upgrades — v1.0.1 "Launch Ops" + v1.1.0 "Progress Pulse" Design Spec

**Status:** Designed. v1.0.1 is mostly operator work + one small PR; v1.1.0 gets a TDD plan under `docs/superpowers/plans/`.
**Date:** 2026-07-10.
**Author:** Claude (Fable 5) with Shaan.

---

## 1. Context & goal

Shaan received the **GitHub Student Developer Pack** (2026-07). This spec maps its perks onto Skill Issue and turns the useful ones into two versioned slices:

- **v1.0.1 — Launch Ops:** the pack unblocks the blocking items in both open sections of [`docs/LAUNCH.md`](../../LAUNCH.md): the production domain (§2, free via the pack's .TECH offer) and the 100 RPS load test (§1, runnable on a DigitalOcean credit droplet instead of the OOM-prone laptop). The remaining §1 item — professional legal review of `/privacy` + `/terms` — stays a human errand outside this slice. Plus a Sentry quota upgrade with session replay for launch-day watching.
- **v1.1.0 — Progress Pulse:** the one genuinely *new* capability in the pack — Mailgun (20K emails/month, 12 months) — powers an opt-in **monthly score-change digest**. This implements the "Engineering Evolution Tracking" idea from PLAN.md "Beyond v1.0" and gives the product the retention loop it lacks (today a user gets roasted once, shares, never returns).

Everything else in the pack is either redundant with the current stack or personal tooling — audited in §6 so nothing is silently dropped.

## 2. Locked scope decisions (2026-07-10)

| Decision | Choice | Why |
| --- | --- | --- |
| Production domain | **skillissue.tech** | Exact brand, no hyphen; **available** (verified 2026-07-10) and **free year 1** via the pack's .TECH offer. Alternatives: most `skillissue.*` TLDs (.me/.dev/.gg/.io/.app/.lol/.com-variants) are taken; `skillissu.me` / `skill-issue.me` are free via Namecheap but weaker for a viral consumer brand; `skillissue.report` (~$12/yr) not pack-covered |
| Where to redeem | Pack portal (get.tech), **not** Vercel | The free year only applies through the pack; Vercel would charge $7.99. DNS then points at Vercel (or uses Vercel nameservers) |
| Email slice shape | **Monthly digest only** | One-shot "email me my report" duplicates share links (YAGNI). Weekly cadence rejected — GitHub activity moves too slowly; most weeklies would say "nothing changed" |
| Digest content | **Deterministic only** — score/tier/bucket deltas, badges gained/lost, report link | No LLM in email: cheap, run-stable, on-philosophy ("engineering insight first, AI flavor second") |
| Send policy | Send **only when something changed** (total, any bucket, tier, or badges); always update the stored snapshot | A monthly "nothing changed" email is spam and burns deliverability |
| Email capture | **Typed address + double opt-in confirm link** — never from OAuth | v0.9.5 deliberately cut the OAuth scope to `read:user`; reading emails would re-widen it. Double opt-in is also the clean legal posture |
| Sender domain | **mg.skillissue.tech** subdomain, SPF/DKIM in the domain's DNS | Digest deliverability can't taint the root domain |
| Mailgun wiring | REST API via existing `httpx` | No SDK dependency for two endpoints (send + nothing else) |
| Digest cron shape | **Daily cron, due-based selection** (subs with `last_digest_at` > 30 days), batch-capped per run | Self-draining and self-retrying; a failed sub is picked up the next day. Mirrors the v0.8.1 cron + `CRON_SECRET` pattern |
| Observability upgrades | **Sentry education plan only**; skip Datadog / New Relic / Honeybadger / Simple Analytics | Sentry + PostHog already cover errors + analytics; a third dashboard is surface area, not signal |
| Load-test runner | One-off DigitalOcean droplet (4–8 GB), destroyed after | The harness runs the whole stack locally (Docker + SRH) on the droplet — no prod risk, no laptop OOM |

## 3. Slice A — v1.0.1 "Launch Ops"

Mostly operator actions; the only code is Sentry config + docs. Ships as a patch release per AGENTS.md rule 3.

### 3.1 Operator checklist (in order)

1. **Redeem pack offers:** GitHub Pro (automatic), .TECH domain, Sentry education plan (applied to the existing Sentry org), DigitalOcean credit, Mailgun (needed in v1.1.0 — redeem now, wire later). Offer terms change; verify amounts at redemption — nothing in this plan depends on exact dollar values.
2. **Register skillissue.tech** at the pack portal. Add the domain to the Vercel project (Settings → Domains), create the DNS records Vercel shows (or delegate nameservers to Vercel — preferred, so v1.1.0's Mailgun records live in one place). Keep `skill-issue-tau.vercel.app` as a 308 redirect to the new domain (Vercel default-domain redirect setting).
3. **Host cutover (one maintenance window):** update `CORS_ALLOW_ORIGINS`, `OAUTH_REDIRECT_URL`, `FRONTEND_BASE_URL`, `NEXT_PUBLIC_SITE_URL` on Vercel **and** the GitHub OAuth App callback URL together; redeploy; immediately verify sign-in end-to-end, an analysis run, `/me`, and a `/share/<slug>` link on the new domain. Rollback = revert the env values to the vercel.app host.
4. **Load test:** create a 4–8 GB droplet, install Docker, run the warm-`/analyze` 100 RPS test per [`backend/loadtest/README.md`](../../../backend/loadtest/README.md), record max sustainable RPS + p95 in `docs/PROGRESS_LOG.md`, destroy the droplet.
5. **Calendar reminders:** .tech renewal (~$40–50/yr standard pricing — decide renew vs transfer before 2027-07) and Mailgun offer expiry (2027-07, see §5).

### 3.2 Code changes (one small PR)

| File | Change |
| --- | --- |
| `frontend/src/observability/sentry.client.ts` | Enable Session Replay: `replaysOnErrorSampleRate: 1.0`, `replaysSessionSampleRate: 0.1`; raise `tracesSampleRate` (env-tunable, start ~0.2) now that the education plan's 100K-transaction budget exists |
| `backend/app/settings.py` / Vercel env | Raise the backend `traces_sample_rate` env value to match; retune after a week of real launch traffic |
| `docs/LAUNCH.md` | Check off §1 load test + §2 domain items as they complete; note the pack redemption route |
| Footer / README / repo links | Point at `https://skillissue.tech` where the vercel.app host is hard-coded in copy |

### 3.3 Exit criteria

- [ ] skillissue.tech serves the app with valid SSL; vercel.app host redirects.
- [ ] OAuth sign-in verified end-to-end on the new domain (callback URL updated).
- [ ] A forced test error produces a Sentry event **with session replay attached**.
- [ ] 100 RPS load-test result (max RPS + p95) recorded in `docs/PROGRESS_LOG.md`.
- [ ] `CHANGELOG.md` `[1.0.1]` + version literals bumped; tag `v1.0.1`; release published.

## 4. Slice B — v1.1.0 "Progress Pulse"

### 4.1 Architecture (one paragraph)

A new `email_subscriptions` table (one row per user, cascade-deleted with the account) stores a typed email address, double-opt-in state, token hashes, the last digest snapshot, and `last_digest_at`. A daily Vercel cron route (same `CRON_SECRET` auth pattern as `/cron/refresh-saved-analyses`) selects confirmed subscriptions due for a digest (>30 days since last), re-analyzes each username via the existing refresh path (`app/persistence/refresh.py` — all four cache layers apply), computes deterministic deltas against the stored snapshot, and — only if something changed — renders a minimal inline-styled HTML email and sends it through Mailgun's REST API via `httpx`. Every per-subscription step fails open: an error logs to Sentry, the sub is skipped, and the due-based selection naturally retries it tomorrow. Confirm and unsubscribe are one-click tokenized GET routes requiring no session (links work from any mail client); tokens are stored hashed, same discipline as `app/cron/tokens.py`.

### 4.2 Surface area

**New — backend**

| File | Responsibility |
| --- | --- |
| `app/db/models.py::EmailSubscription` | `id`, `user_id` (FK unique, cascade), `email`, `confirm_token_hash`, `confirmed_at`, `unsubscribe_token_hash`, `last_digest_snapshot` (JSONB: total, tier, per-bucket, badge slugs), `last_digest_at`, `created_at`, `updated_at` |
| `app/persistence/subscriptions.py` | CRUD + `select_due(limit)` query (confirmed, `last_digest_at IS NULL OR < now()-30d`) |
| `app/email/mailgun.py` | Thin `httpx` sender: `send(to, subject, html)` against the Mailgun REST API; `MAILGUN_API_KEY` / `MAILGUN_DOMAIN` settings; timeout + explicit error surface |
| `app/email/digest.py` | Delta computation (pure function: previous snapshot × new report → `DigestDelta | None`) + HTML/text template rendering |
| `app/routers/digest.py` | `POST /me/digest` (session auth: create/replace sub, send confirm email) · `DELETE /me/digest` (session auth) · `GET /digest/confirm?token=` (token valid 48 h; expired → status page prompts re-submitting the form) · `GET /digest/unsubscribe?token=` (never expires) — both tokenized, no session, redirect to a frontend status page |
| `app/cron/digest.py` | Batch runner: select due → refresh → delta → send-if-changed → update snapshot + `last_digest_at`; per-sub fail-open |
| `tests/…` | Delta function (deterministic — full coverage), due-selection, token confirm/unsub flows, send-if-changed policy, template snapshot, fail-open batch, Mailgun stub |

**New — frontend**

| File | Responsibility |
| --- | --- |
| `/me` digest card component | Opt-in state machine: enter email → "check your inbox" → confirmed / unsubscribe. Responsive at 320/375/414/768/desktop per house rule |
| `/digest/[status]` page | Landing for confirm/unsubscribe redirects (confirmed, expired, unsubscribed) |

**Modified**

| File | Change |
| --- | --- |
| `vercel.ts` | Add daily cron entry for `/_/backend/cron/send-digests` |
| `app/settings.py` | `MAILGUN_API_KEY`, `MAILGUN_DOMAIN`, `DIGEST_BATCH_SIZE` (default ~100), `DIGEST_INTERVAL_DAYS` (default 30) |
| `frontend/src/app/privacy/page.tsx` | Email-communications clause: what we store (address, opt-in state), why, unsubscribe/delete behavior |
| `docs/OBSERVABILITY.md` / `ARCHITECTURE.md` / `docs/TECH_STACK.md` | Document the email subsystem + cron |

### 4.3 Email content & deliverability rules

- Subject pattern: `Your Skill Issue moved: 71 → 74` (or badge-led when score is flat).
- Body: score delta, tier (+sub-rank) change, per-bucket deltas, badges gained/lost, one CTA link to the report. **No narrative text.** Brand-consistent but email-client-safe (inline styles, light background, no webfonts).
- Every send carries an unsubscribe link **and** `List-Unsubscribe` / `List-Unsubscribe-Post` headers.
- SPF + DKIM on `mg.skillissue.tech` before the first send; volume ramps naturally (opt-in only), no warm-up scheme needed.
- Budget: Mailgun pack tier is 20K/month; `DIGEST_BATCH_SIZE` bounds cron duration, not spend.

### 4.4 Exit criteria

- [ ] Full opt-in loop verified in prod: type email → confirm link → confirmed state on `/me`.
- [ ] Cron run against a due subscription produces either a correct digest email (verified received, renders in Gmail dark/light) or a clean "no change, snapshot updated" skip.
- [ ] Unsubscribe link works from the received email without a session; `/me` reflects it.
- [ ] Delta computation unit-tested across: score up/down/flat, tier change, badge gain/loss, first-ever digest (no snapshot → treat as changed).
- [ ] A mid-batch failure (stubbed refresh error) skips that sub, logs to Sentry, and completes the rest.
- [ ] Privacy page updated; `CHANGELOG.md` `[1.1.0]`; tag `v1.1.0`; release published.

## 5. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| OAuth breaks during host cutover | Env + callback updated together in one window; immediate e2e verify; rollback is reverting env values |
| .tech renewal price (~$40–50/yr after free year) | Calendar reminder before 2027-07; decide renew / transfer / re-evaluate then. Domain is in the share-card URL, so treat as sticky once launched |
| Pack offers change or differ at redemption | Plan depends on capabilities, not dollar amounts; verify each offer's current terms when redeeming |
| Mailgun offer expires 2027-07 | Digest volume by then likely fits a cheap tier; sender is isolated behind `app/email/mailgun.py`, so swapping providers (e.g. Resend) touches one file |
| Fresh-subdomain deliverability | Double opt-in only, changed-only sends, List-Unsubscribe headers, SPF/DKIM from day one |
| Digest re-analysis burns GitHub/Groq quota | Refresh path reuses all four cache layers; no LLM in digests; batch cap bounds any single run |
| Multi-source future (GitLab/LinkedIn) | `email_subscriptions` is source-agnostic (user + email + snapshot); nothing GitHub-specific in the schema |

## 6. Appendix — full pack audit (verified against the official partner FAQ, 2026-07-10)

| Perk | Offer | Verdict for Skill Issue |
| --- | --- | --- |
| .TECH Domains | 1 free .tech for 1 year | **USE — v1.0.1.** skillissue.tech |
| Namecheap | Free .me for 1 year + SSL cert | **Optional.** `skillissu.me` is available (domain hack); grab defensively and 308-redirect to skillissue.tech if desired. The SSL cert is unneeded (Vercel auto-SSL) |
| Name.com | 1 free year domain + Advanced Security | **Hold in reserve** — a second defensive TLD later if the brand takes off |
| Sentry | Education plan: 50K errors / 100K transactions / 1 GB attachments / 500 replays, 1 year | **USE — v1.0.1.** Already integrated both services; unlocks replay + higher trace sampling |
| DigitalOcean | ~$100–200 credit, 1 year | **USE — v1.0.1.** One-off load-test droplet; keep remainder for future staging needs |
| Mailgun | 20K emails/mo + 100 validations/mo, 12 months | **USE — v1.1.0.** Progress Pulse digests |
| GitHub Pro + Copilot | Free while student | **USE — personal.** Also: Codespaces hours sidestep the local `next dev` OOM problem |
| Polypane | Free 1 year | **USE — personal tooling.** Multi-breakpoint browser; pairs with the responsive-is-non-negotiable rule |
| BrowserStack / LambdaTest | Automate Mobile 1 yr / Live plan 1 yr | **USE — personal tooling.** Real-device checks before releases |
| JetBrains | All-products pack while student | **USE — personal tooling.** PyCharm Pro for the FastAPI side |
| Notion | Education plan | **USE — personal.** Planning/notes |
| Datadog | Pro, 10 servers, 2 years | **SKIP.** Redundant with Sentry + PostHog; third dashboard = surface area, not signal |
| New Relic | Free while student | **SKIP.** Same reason |
| Honeybadger | Small account, 1 year | **SKIP.** Same reason |
| Simple Analytics / Freshpaint | Starter 1 yr / Growth while enrolled | **SKIP.** PostHog covers product analytics |
| Heroku | $13/mo credit, 24 months | **SKIP.** Vercel is the platform; no second host |
| Microsoft Azure | $100 credit | **SKIP.** No Azure dependency; not worth introducing one |
| MongoDB Atlas | $50 credit | **SKIP.** Neon Postgres is the store |
| LocalStack | Free license | **SKIP.** No AWS surface |
| GitKraken / Tower | 6 mo free + discount / free while student | **SKIP.** Git CLI + IDE integration suffice |
| Learning (Educative, FrontendMasters, GoRails, etc.) | Various free periods | **Personal** — outside project scope |

## 7. Out of scope

- Launch posts, on-call, retro — remain operator items in `docs/LAUNCH.md` §3–4.
- One-shot "email me this report", weekly cadence, per-user cadence settings — rejected above; revisit only on real user demand.
- Any new observability vendor, second hosting platform, or AWS emulation.
- GitLab / LinkedIn / Resume checkers — unchanged in "Beyond v1.0"; nothing here blocks them.
