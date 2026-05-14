# Changelog

All notable changes to **Skill Issue** are recorded here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every version listed here must correspond to a slice in [`PLAN.md`](./PLAN.md) whose exit criteria have been met.

---

## [Unreleased]

Nothing yet. Next slice: **v0.1.0 — Backend MVP** (see [`PLAN.md`](./PLAN.md)).

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
