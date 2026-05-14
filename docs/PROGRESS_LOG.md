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
