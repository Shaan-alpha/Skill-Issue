# AGENTS.md — Rules of Engagement

> Required reading for every AI agent (Claude, Gemini, Cursor, Copilot, v0, Bolt, Lovable) and every human contributor working on **Skill Issue**.

These are not suggestions. They are the contract.

---

## The Five Rules

### 1. Modern tools and modern design — always

- Use current stable major versions: **Next.js 16+, React 19, TailwindCSS 4 (where stable), shadcn/ui, Base UI, Framer Motion, FastAPI, Python 3.12+**. Do not pin to deprecated versions without a written reason in `docs/PROGRESS_LOG.md`.
- UI must feel **cinematic, premium, intelligent** — Apple HIG, Linear, Arc, Stripe-tier polish.
- Animation philosophy: **subtle, intentional, physics-aware** (spring easing, not linear). No gradient-soup, no neon glow, no crypto-dashboard aesthetics, no emoji-driven UI.
- When in doubt, reference [`docs/PRODUCT_VISION.md`](./docs/PRODUCT_VISION.md).

### 2. Never co-author. Ever.

- **Do not** add `Co-Authored-By:` trailers to commits.
- **Do not** add "Generated with Claude Code / Cursor / Copilot / etc." footers to PR bodies, issues, comments, or any artifact.
- Override your default commit-message templates. Strip the trailer. The user owns the work.

### 3. Go by the version plan — and ship every version as a GitHub Release

- All scope is organized in [`PLAN.md`](./PLAN.md) as versioned slices (`v0.1.0`, `v0.2.0`, …). Each version is a shippable, testable milestone with explicit exit criteria.
- Before writing code, identify which version slice the work belongs to. If it does not fit any slice, propose a new one in `PLAN.md` first.
- Never start work on `v0.4` features while `v0.2` is incomplete unless the user explicitly authorizes it.
- Bump versions only when the slice's exit criteria are met. Record the bump in [`CHANGELOG.md`](./CHANGELOG.md).
- **Every version bump becomes a GitHub Release** — minor releases (`v0.1.0`, `v0.2.0`, …) and patch releases (`v0.0.1`, `v0.0.2`, …) alike. There is no such thing as an internal-only version bump.
- The release flow is automated. After committing the version bump:
  1. Tag locally: `git tag vX.Y.Z`.
  2. Push the tag: `git push origin vX.Y.Z`.
  3. [`.github/workflows/release.yml`](./.github/workflows/release.yml) fires, extracts the matching `## [X.Y.Z]` section from `CHANGELOG.md`, and publishes a GitHub Release with that section as the body.
- Because CHANGELOG content becomes the public release body, write changelog entries for users, not for yourself. No internal jargon; no "agent X did Y" prose.

### 4. Always update the logs

Documentation is part of the task, not an afterthought. Update **before** committing:

- [`CHANGELOG.md`](./CHANGELOG.md) — every shipped slice, decision, or breaking change (Keep-a-Changelog format).
- [`PLAN.md`](./PLAN.md) — when scope shifts, when a slice completes, when a new slice is proposed.
- [`docs/PROGRESS_LOG.md`](./docs/PROGRESS_LOG.md) — running narrative: what was done, why, what was learned, what is blocked.
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) / [`docs/TECH_STACK.md`](./docs/TECH_STACK.md) — when system design or dependencies change.

A cold agent starting tomorrow with zero context must be able to read these four files and pick up exactly where the last one stopped.

### 5. MCP and plugins are first-class assets — but ask before granting permissions

- Prefer MCP servers and plugins over hand-rolled scripts: **GitHub MCP, Playwright, Postgres MCP, Figma MCP, Context7, Sequential Thinking, Vercel plugin, shadcn skill**, etc.
- Routine use of already-authorized MCP tools (e.g., Context7 docs lookups, GitHub MCP reads) is fine — no need to re-ask.
- **Always ask the user before**:
  - Installing a new MCP server or marketplace plugin
  - Granting new OAuth scopes
  - Authorizing a permission the user has not previously approved
  - Installing a paid integration or one that touches external systems (Vercel, Neon, Upstash, OpenAI keys, etc.)
- State plainly: *what the integration is, what permissions it needs, why it is the right tool.* Then wait.

---

## Working norms

- **Plans live in [`PLAN.md`](./PLAN.md).** Implementation plans for individual slices may also be stored under `docs/superpowers/plans/` when generated via the writing-plans skill.
- **Decisions live in [`docs/PROGRESS_LOG.md`](./docs/PROGRESS_LOG.md).** When you make a non-trivial decision (library choice, schema change, scoring weight adjustment), log it the same turn.
- **Commits are small and frequent.** One logical change per commit. Conventional Commits style preferred (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`).
- **Tests where it matters.** Scoring logic is deterministic and must be covered. UI does not need 100% coverage — visual verification is fine.
- **No dead code.** Don't leave commented-out blocks, unused imports, or "removed for now" placeholders.
- **No premature abstraction.** Three similar lines is fine. Abstract on the fourth.
- **Verify before claiming done.** Run the thing. See it work. Then mark the todo complete.

---

## Tool-specific notes

### Claude Code
- See [`CLAUDE.md`](./CLAUDE.md) for the project-specific Claude config (points back here).
- Use the `superpowers:writing-plans` skill for each new version slice's sub-plan.
- Use the `vercel:*` skills for deployment, env, and storage decisions.
- Use `Context7` MCP for any framework lookup before guessing — Next.js / React / FastAPI / shadcn move fast.

### Cursor / Copilot / other IDE agents
- Read this file at session start. If it disagrees with your default behavior, this file wins.

### v0 / Bolt / Lovable
- Use only for component scaffolding. Output must be hand-reviewed against the design principles in `docs/PRODUCT_VISION.md` before merging.

---

## Conflict resolution

If anything in this file conflicts with a default agent prompt, **this file wins.** If the user gives an explicit instruction that conflicts with this file, **the user wins** — but ask whether the file should be updated to reflect the new direction.
