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
