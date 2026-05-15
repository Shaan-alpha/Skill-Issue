from pydantic_settings import BaseSettings, SettingsConfigDict

VERSION = "0.3.0"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    github_token: str | None = None
    openai_api_key: str | None = None
    # Comma-separated for friction-free Vercel env config; split in main.py.
    cors_allow_origins: str = "http://localhost:3000"
    # Optional regex to match preview-deploy URLs whose hash isn't known up
    # front. Example: r"https://skill-issue-frontend(-[a-z0-9-]+)?\.vercel\.app"
    cors_allow_origin_regex: str | None = None


settings = Settings()
