from pydantic_settings import BaseSettings, SettingsConfigDict

VERSION = "0.7.3"


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


settings = Settings()
