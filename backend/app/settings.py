from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

VERSION = "1.0.3"


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
    # Fail closed: default the session/OAuth-state cookies to Secure so any
    # environment that forgets to set COOKIE_SECURE still ships hardened
    # cookies. Local HTTP dev must opt out with COOKIE_SECURE=false (browsers
    # won't send Secure cookies over http://localhost).
    cookie_secure: bool = True

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

    # v0.9.2 — rate limiting (IP + user)
    # Hourly caps per UTC-hour bucket. Anonymous callers are capped per-IP;
    # signed-in callers per-user (they bring their own GitHub token). Narrative
    # ~1.5x analyze because one analysis view can fire both Roast and Mentor.
    analyze_anon_per_ip_per_hour: int = 20
    analyze_user_per_hour: int = 60
    narrative_anon_per_ip_per_hour: int = 30
    narrative_user_per_hour: int = 90
    # Shared secret authenticating the Next.js RSC -> backend hop so a forwarded
    # X-Client-IP can be trusted for proxied anonymous /analyze. Set the SAME
    # value on both the frontend and backend services. When unset, anonymous
    # /analyze enforcement is skipped (otherwise all website visitors would
    # collapse into one Vercel-infra-IP bucket); narrative + user limits stay on.
    internal_proxy_secret: str | None = None

    # v0.9.4 — DB connection pool sizing
    # SQLAlchemy async engine pool. Defaults match the pre-v0.9.4 hardcoded
    # values, so a deploy with neither env var set is byte-identical to before.
    # Raise via env only when RUM shows pool exhaustion (QueuePool timeouts).
    # Ceiling: ~105 usable Postgres connections (112 max_connections - 7
    # reserved on the current ~0.25 CU Neon compute). On the PgBouncer pooler
    # this is buffered by multiplexing; on a direct connection keep
    # (pool_size + max_overflow) x peak_instances < 105.
    db_pool_size: int = 5
    db_max_overflow: int = 5


settings = Settings()
