from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

VERSION = "0.8.7"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    github_token: str | None = None
    openai_api_key: str | None = None
    # Comma-separated for friction-free Vercel env config; split in main.py.
    cors_allow_origins: str = "http://localhost:3000"
    # Optional regex to match preview-deploy URLs whose hash isn't known up
    # front. Example: r"https://skill-issue-frontend(-[a-z0-9-]+)?\.vercel\.app"
    cors_allow_origin_regex: str | None = None

    # v0.4.0 narrative layer.
    narrative_model: str = "gpt-4o"
    narrative_daily_limit: int = 50
    # Optional OpenAI-compatible base URL. Set to point at any provider that
    # ships an OpenAI-compatible chat API (Groq, OpenRouter, Cerebras, vLLM,
    # Ollama, etc.) instead of OpenAI's default endpoint.
    narrative_base_url: str | None = None

    # v0.5.0 — Auth + persistence
    database_url: str | None = None
    database_direct_url: str | None = None
    github_oauth_client_id: str | None = None
    github_oauth_client_secret: str | None = None
    oauth_redirect_url: str | None = None
    session_token_enc_key: str | None = None
    session_cookie_name: str = "si_session"
    session_ttl_days: int = 30
    cookie_domain: str | None = None
    cookie_secure: bool = False

    # v0.7.0 — caching
    upstash_redis_rest_url: str | None = None
    upstash_redis_rest_token: str | None = None
    # 6 hours — Report cache.
    cache_report_ttl_seconds: int = 21_600
    # 15 minutes — fallback TTL for layers that don't pick a specific one.
    cache_default_ttl_seconds: int = 900

    # v0.8.0 — observability
    sentry_dsn: str | None = None
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "json"  # "json" in prod, "console" in dev

    # v0.8.1 — cron auth
    # Bearer token verified by app.routers.cron.require_cron_auth.
    # Vercel Cron injects "Authorization: Bearer ${CRON_SECRET}" automatically
    # when this env var is set on the project. When unset, the cron route
    # responds 503 so misconfig is visible at the first fire instead of
    # silently no-op'ing.
    cron_secret: str | None = None

    # v0.8.2 — force-refresh rate limit
    # Per-user cap on force-refresh actions per UTC hour. Reset on bucket
    # rollover. Override via env FORCE_REFRESH_PER_USER_PER_HOUR.
    force_refresh_per_user_per_hour: int = 10

    # v0.9.0 — ingestion fan-out cap
    # Per-call asyncio.Semaphore limit applied to GH API requests inside
    # ingest_profile. Caps the burst from `_enrich_repo_signals` (≤20 root
    # contents) and `list_commits` (≤10 commits). Default 8 keeps a single
    # analysis well inside GitHub's secondary rate-limit threshold. Override
    # via env GH_INGEST_CONCURRENCY without a redeploy.
    gh_ingest_concurrency: int = 8

    # v0.8.6 — on-demand /share/[slug] ISR revalidation
    # FRONTEND_BASE_URL: backend posts to {FRONTEND_BASE_URL}/api/revalidate
    # after every share toggle to bust the per-slug cache tag.
    # REVALIDATE_SECRET: shared secret (constant-time compared on both sides)
    # authenticating the backend → frontend invalidation webhook.
    # When either is unset, share toggles still work but the frontend ISR
    # cache only revalidates at its 3600s cacheLife TTL (graceful degradation).
    frontend_base_url: str | None = None
    revalidate_secret: str | None = None


settings = Settings()
