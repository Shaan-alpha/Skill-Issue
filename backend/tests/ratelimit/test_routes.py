from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import settings as settings_module
from app.db.session import get_db
from app.dependencies import get_narrative_service, get_report_for_user
from app.main import app


async def _fake_db():
    yield object()


@pytest.fixture
def client(monkeypatch, fake_cache):
    monkeypatch.setattr("app.ratelimit.get_cache", lambda: fake_cache)
    app.dependency_overrides[get_db] = _fake_db
    app.dependency_overrides[get_report_for_user] = lambda: MagicMock()
    app.dependency_overrides[get_narrative_service] = lambda: MagicMock()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_analyze_429_when_anon_cap_is_zero(client, monkeypatch):
    # Secret set so anon enforcement is active; cap 0 trips on the first call,
    # short-circuiting before the (stubbed) report handler body runs.
    monkeypatch.setattr(settings_module.settings, "internal_proxy_secret", "s")
    monkeypatch.setattr(settings_module.settings, "analyze_anon_per_ip_per_hour", 0)
    res = client.get("/analyze/octocat", headers={"x-real-ip": "8.8.8.8"})
    assert res.status_code == 429
    body = res.json()
    assert body["error"] == "rate_limited"
    assert isinstance(body["retry_after_seconds"], int)
    assert "Retry-After" in res.headers  # preserved through the exception handler


def test_narrative_429_when_anon_cap_is_zero(client, monkeypatch):
    monkeypatch.setattr(settings_module.settings, "narrative_anon_per_ip_per_hour", 0)
    res = client.get("/narrative/octocat?mode=roast", headers={"x-real-ip": "8.8.8.8"})
    assert res.status_code == 429
    assert res.headers["Retry-After"]
