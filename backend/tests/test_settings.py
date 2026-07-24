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
    for k in (
        "DATABASE_URL",
        "DATABASE_DIRECT_URL",
        "GITHUB_OAUTH_CLIENT_ID",
        "GITHUB_OAUTH_CLIENT_SECRET",
        "OAUTH_REDIRECT_URL",
        "SESSION_TOKEN_ENC_KEY",
    ):
        monkeypatch.setenv(
            k, "placeholder" if "URL" not in k else "postgresql+asyncpg://u:p@h:6543/d"
        )
    monkeypatch.setenv("SESSION_TOKEN_ENC_KEY", "A" * 44)
    monkeypatch.setenv("SESSION_TTL_DAYS", "7")

    assert Settings().session_ttl_days == 7


def test_v1_0_4_cost_control_defaults():
    s = Settings()
    assert s.narrative_daily_limit == 500
    assert s.narrative_anon_ip_daily_limit == 10
    assert s.narrative_user_daily_limit == 40
    assert s.trusted_client_ip_header == "x-forwarded-for"
    assert s.analyze_unattributed_per_hour == 300


def test_v1_0_5_amplification_defaults():
    s = Settings()
    assert s.gh_max_calls_per_analysis == 150
    assert s.github_retry_after_ceiling_seconds == 10.0
    assert s.analyze_ingest_deadline_seconds == 45.0


def test_v1_0_6_breaker_default():
    assert Settings().gh_shared_token_min_remaining == 500
