from app.settings import Settings


def test_required_v050_fields_loaded(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@host:6543/db")
    monkeypatch.setenv("DATABASE_DIRECT_URL", "postgresql+asyncpg://u:p@host:5432/db")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_ID", "abc")
    monkeypatch.setenv("GITHUB_OAUTH_CLIENT_SECRET", "shh")
    monkeypatch.setenv("OAUTH_REDIRECT_URL", "http://localhost:8000/auth/callback")
    # 32 raw bytes, base64-encoded
    monkeypatch.setenv("SESSION_TOKEN_ENC_KEY", "A" * 44)  # 32B b64 padded

    s = Settings()
    assert str(s.database_url).startswith("postgresql+asyncpg://")
    assert s.github_oauth_client_id == "abc"
    assert s.session_ttl_days == 30
    assert s.session_cookie_name == "si_session"


def test_session_ttl_overridable(monkeypatch):
    for k in ("DATABASE_URL", "DATABASE_DIRECT_URL", "GITHUB_OAUTH_CLIENT_ID",
              "GITHUB_OAUTH_CLIENT_SECRET", "OAUTH_REDIRECT_URL", "SESSION_TOKEN_ENC_KEY"):
        monkeypatch.setenv(k, "placeholder" if "URL" not in k else "postgresql+asyncpg://u:p@h:6543/d")
    monkeypatch.setenv("SESSION_TOKEN_ENC_KEY", "A" * 44)
    monkeypatch.setenv("SESSION_TTL_DAYS", "7")

    assert Settings().session_ttl_days == 7
