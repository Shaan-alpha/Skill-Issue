"""Tests for the Sentry before_send PII scrub hook."""

from __future__ import annotations

import copy

from app.observability.sentry import init_sentry, scrub_event


def test_scrub_removes_cookie_header_from_request():
    event = {
        "request": {
            "headers": {
                "Cookie": "si_session=secret",
                "User-Agent": "pytest",
            }
        }
    }
    scrubbed = scrub_event(copy.deepcopy(event), {})
    assert "Cookie" not in scrubbed["request"]["headers"]
    assert "cookie" not in {k.lower() for k in scrubbed["request"]["headers"]}
    assert scrubbed["request"]["headers"]["User-Agent"] == "pytest"


def test_scrub_removes_authorization_header():
    event = {"request": {"headers": {"Authorization": "Bearer secret-token"}}}
    scrubbed = scrub_event(copy.deepcopy(event), {})
    assert scrubbed["request"]["headers"] == {}


def test_scrub_strips_internal_and_ip_headers():
    event = {
        "request": {
            "headers": {
                "X-Internal-Secret": "supersecret",
                "X-Revalidate-Secret": "revsecret",
                "X-Client-IP": "9.9.9.9",
                "X-Forwarded-For": "9.9.9.9",
                "X-Real-IP": "9.9.9.9",
                "Accept": "application/json",
            }
        }
    }
    out = scrub_event(copy.deepcopy(event), {})
    headers = out["request"]["headers"]
    assert "Accept" in headers
    for gone in (
        "X-Internal-Secret",
        "X-Revalidate-Secret",
        "X-Client-IP",
        "X-Forwarded-For",
        "X-Real-IP",
    ):
        assert gone not in headers


def test_scrub_removes_set_cookie_response_header():
    event = {
        "extra": {
            "response_headers": {
                "Set-Cookie": "si_session=secret; Path=/; HttpOnly",
            }
        }
    }
    scrubbed = scrub_event(copy.deepcopy(event), {})
    assert "Set-Cookie" not in scrubbed["extra"]["response_headers"]


def test_scrub_removes_known_pii_fields_from_extra():
    event = {
        "extra": {
            "access_token": "gho_supersecret",
            "access_token_ct": b"\x01\x02\x03",
            "oauth_state": "state-token",
            "oauth_code": "code-token",
            "session_id": "raw-session",
            "email": "shaan@example.com",
            "innocent_field": "kept",
        }
    }
    scrubbed = scrub_event(copy.deepcopy(event), {})
    extra = scrubbed["extra"]
    for k in (
        "access_token",
        "access_token_ct",
        "oauth_state",
        "oauth_code",
        "session_id",
        "email",
    ):
        assert k not in extra, f"{k} was not scrubbed"
    assert extra["innocent_field"] == "kept"


def test_scrub_drops_user_email_when_present():
    event = {"user": {"id": "u1", "email": "user@example.com"}}
    scrubbed = scrub_event(copy.deepcopy(event), {})
    assert scrubbed["user"]["id"] == "u1"
    assert "email" not in scrubbed["user"]


def test_scrub_is_recursive_for_nested_dicts():
    event = {
        "contexts": {
            "auth": {
                "access_token": "should-be-scrubbed",
                "kept": "yes",
            }
        }
    }
    scrubbed = scrub_event(copy.deepcopy(event), {})
    assert "access_token" not in scrubbed["contexts"]["auth"]
    assert scrubbed["contexts"]["auth"]["kept"] == "yes"


def test_scrub_handles_missing_sections_gracefully():
    """Real events don't always have every section."""
    scrub_event({}, {})
    scrub_event({"message": "hi"}, {})
    scrub_event({"request": None}, {})  # must not raise


def test_init_sentry_is_noop_when_dsn_unset(monkeypatch):
    """No DSN → no init call. Code that fires later (capture_exception) is a
    no-op rather than crashing the app."""
    called: dict[str, bool] = {"init": False}

    def _fake_init(**kwargs):
        called["init"] = True

    monkeypatch.setattr("sentry_sdk.init", _fake_init)
    init_sentry(dsn=None, environment="test", traces_sample_rate=0.1, release="0.8.0")
    assert called["init"] is False


def test_init_sentry_calls_sdk_when_dsn_set(monkeypatch):
    captured: dict = {}

    def _fake_init(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("sentry_sdk.init", _fake_init)
    init_sentry(
        dsn="https://abc@o123.ingest.sentry.io/456",
        environment="production",
        traces_sample_rate=0.25,
        release="0.8.0",
    )
    assert captured["dsn"] == "https://abc@o123.ingest.sentry.io/456"
    assert captured["environment"] == "production"
    assert captured["traces_sample_rate"] == 0.25
    assert captured["release"] == "0.8.0"
    assert captured["send_default_pii"] is False
    assert callable(captured["before_send"])


def test_init_sentry_skips_when_already_initialised(monkeypatch):
    """A second init_sentry call should NOT create a second client."""
    init_calls: list[dict] = []

    def _fake_init(**kwargs):
        init_calls.append(kwargs)

    monkeypatch.setattr("sentry_sdk.init", _fake_init)
    monkeypatch.setattr("sentry_sdk.is_initialized", lambda: True)

    init_sentry(
        dsn="https://abc@o123.ingest.sentry.io/456",
        environment="production",
        traces_sample_rate=0.1,
        release="0.8.0",
    )
    assert init_calls == []  # second call skipped
