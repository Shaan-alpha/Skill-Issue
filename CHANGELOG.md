# Changelog

All notable changes to **Skill Issue** are recorded here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Every version listed here must correspond to a slice in [`PLAN.md`](./PLAN.md) whose exit criteria have been met.

---

## [Unreleased]

### Added
- Backend MVP skeleton using FastAPI, Pydantic v2, and `uv`.
- Async GitHub client with REST/GraphQL support and robust rate-limit handling.
- Deterministic scoring engine with scorers for `repo_quality` (30 pts), `engineering_maturity` (20 pts), `oss_collab` (15 pts), and `consistency` (10 pts).
- Ingestion layer for GitHub profiles, pinned repositories, language statistics, external PR/review activity, and multi-repo commit patterns.
- Unit testing suite with fixture profiles for every scorer.


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
