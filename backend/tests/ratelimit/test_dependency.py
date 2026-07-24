from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import settings as settings_module
from app.ratelimit import analyze_rate_limiter, narrative_rate_limiter
from tests.ratelimit.test_identity import make_request


def _signed_in(user_id: int = 7) -> SimpleNamespace:
    return SimpleNamespace(user=SimpleNamespace(id=user_id))


async def test_anon_allowed_then_denied(monkeypatch, fake_cache):
    monkeypatch.setattr("app.ratelimit.get_cache", lambda: fake_cache)
    monkeypatch.setattr(settings_module.settings, "internal_proxy_secret", "s")
    monkeypatch.setattr(settings_module.settings, "analyze_anon_per_ip_per_hour", 2)
    req = make_request({"x-real-ip": "1.1.1.1"})

    # First two anonymous calls pass.
    await analyze_rate_limiter(req, session=None)
    await analyze_rate_limiter(req, session=None)
    # Third trips the cap.
    with pytest.raises(HTTPException) as exc:
        await analyze_rate_limiter(req, session=None)
    assert exc.value.status_code == 429
    assert exc.value.detail["error"] == "rate_limited"
    assert isinstance(exc.value.detail["retry_after_seconds"], int)
    assert "Retry-After" in exc.value.headers


async def test_signed_in_uses_user_limit_not_ip(monkeypatch, fake_cache):
    monkeypatch.setattr("app.ratelimit.get_cache", lambda: fake_cache)
    monkeypatch.setattr(settings_module.settings, "analyze_anon_per_ip_per_hour", 1)
    monkeypatch.setattr(settings_module.settings, "analyze_user_per_hour", 3)
    req = make_request({"x-real-ip": "1.1.1.1"})
    sess = _signed_in()
    # Three signed-in calls under the user cap of 3 — anon cap of 1 must NOT apply.
    await analyze_rate_limiter(req, session=sess)
    await analyze_rate_limiter(req, session=sess)
    await analyze_rate_limiter(req, session=sess)
    with pytest.raises(HTTPException) as exc:
        await analyze_rate_limiter(req, session=sess)
    assert exc.value.status_code == 429


async def test_analyze_secret_unset_uses_unattributed_backstop(monkeypatch, fake_cache):
    # SI-05: secret unset no longer SKIPS anon /analyze — it falls back to a
    # conservative shared `ip:unattributed` backstop, so a direct attacker is
    # still capped (fail-closed, not fail-open).
    monkeypatch.setattr("app.ratelimit.get_cache", lambda: fake_cache)
    monkeypatch.setattr(settings_module.settings, "internal_proxy_secret", None)
    monkeypatch.setattr(settings_module.settings, "analyze_unattributed_per_hour", 2)
    req = make_request({"x-forwarded-for": "1.2.3.4"})
    await analyze_rate_limiter(req, session=None)
    await analyze_rate_limiter(req, session=None)
    with pytest.raises(HTTPException) as exc:
        await analyze_rate_limiter(req, session=None)
    assert exc.value.status_code == 429


async def test_narrative_enforces_anon_even_without_secret(monkeypatch, fake_cache):
    monkeypatch.setattr("app.ratelimit.get_cache", lambda: fake_cache)
    monkeypatch.setattr(settings_module.settings, "internal_proxy_secret", None)
    monkeypatch.setattr(settings_module.settings, "narrative_anon_per_ip_per_hour", 1)
    req = make_request({"x-real-ip": "2.2.2.2"})
    await narrative_rate_limiter(req, session=None)
    with pytest.raises(HTTPException) as exc:
        await narrative_rate_limiter(req, session=None)
    assert exc.value.status_code == 429


async def test_cache_unconfigured_falls_back_to_in_process(monkeypatch):
    # SI-01: cache unconfigured no longer fails OPEN — it degrades to the
    # in-process limiter (conservative), so a 0/limit still blocks.
    from app.ratelimit import in_process_limiter

    in_process_limiter._counts.clear()
    monkeypatch.setattr("app.ratelimit.get_cache", lambda: None)
    monkeypatch.setattr(settings_module.settings, "internal_proxy_secret", "s")
    monkeypatch.setattr(settings_module.settings, "analyze_anon_per_ip_per_hour", 2)
    req = make_request({"x-forwarded-for": "10.0.0.1"})
    await analyze_rate_limiter(req, session=None)
    await analyze_rate_limiter(req, session=None)
    with pytest.raises(HTTPException) as exc:
        await analyze_rate_limiter(req, session=None)
    assert exc.value.status_code == 429


async def test_redis_error_falls_back_to_in_process(monkeypatch, fake_cache, fake_redis):
    # SI-01: a Redis error degrades to the in-process limiter instead of
    # allowing everything (previously fail-open).
    from app.ratelimit import in_process_limiter

    in_process_limiter._counts.clear()
    monkeypatch.setattr("app.ratelimit.get_cache", lambda: fake_cache)
    monkeypatch.setattr(settings_module.settings, "internal_proxy_secret", "s")
    monkeypatch.setattr(settings_module.settings, "analyze_anon_per_ip_per_hour", 1)
    req = make_request({"x-forwarded-for": "10.0.0.2"})
    fake_redis.fail_next = 100  # every INCR errors → RedisCache returns 0 → in-process fallback
    await analyze_rate_limiter(req, session=None)  # in-process 1/1
    with pytest.raises(HTTPException) as exc:
        await analyze_rate_limiter(req, session=None)  # 2 > 1 → 429
    assert exc.value.status_code == 429
