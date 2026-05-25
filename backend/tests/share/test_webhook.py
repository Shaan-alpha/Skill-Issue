from __future__ import annotations

import json as _json
import logging

import httpx
import pytest
import respx

from app import settings as settings_module
from app.share.webhook import revalidate_share_slug


@pytest.fixture
def _configured(monkeypatch):
    """Both env vars set → webhook fires."""
    monkeypatch.setenv("FRONTEND_BASE_URL", "https://frontend.test")
    monkeypatch.setenv("REVALIDATE_SECRET", "supersecret")
    settings_module.settings = settings_module.Settings()


@pytest.fixture
def _unconfigured(monkeypatch):
    """Either var unset → webhook is a logged no-op."""
    monkeypatch.delenv("FRONTEND_BASE_URL", raising=False)
    monkeypatch.delenv("REVALIDATE_SECRET", raising=False)
    settings_module.settings = settings_module.Settings()


async def test_unconfigured_is_no_op(_unconfigured, caplog):
    caplog.set_level(logging.WARNING)
    with respx.mock(assert_all_called=False) as router:
        route = router.post("https://frontend.test/api/revalidate").mock(
            return_value=httpx.Response(204)
        )
        await revalidate_share_slug("abc123")
    assert route.call_count == 0
    assert any("share.revalidate_skipped" in r.message for r in caplog.records)


async def test_happy_path_posts_expected_request(_configured):
    with respx.mock(assert_all_called=True) as router:
        route = router.post("https://frontend.test/api/revalidate").mock(
            return_value=httpx.Response(204)
        )
        await revalidate_share_slug("abc123")
    assert route.call_count == 1
    request = route.calls[0].request
    assert request.headers["X-Revalidate-Secret"] == "supersecret"
    assert request.headers["Content-Type"] == "application/json"
    body = _json.loads(request.content)
    assert body == {"tag": "share:abc123"}


async def test_4xx_is_logged_and_swallowed(_configured, caplog):
    caplog.set_level(logging.WARNING)
    with respx.mock(assert_all_called=True) as router:
        router.post("https://frontend.test/api/revalidate").mock(
            return_value=httpx.Response(401, json={"error": "invalid_secret"})
        )
        # Must NOT raise.
        await revalidate_share_slug("abc123")
    assert any("share.revalidate_failed" in r.message for r in caplog.records)


async def test_network_timeout_is_logged_and_swallowed(_configured, caplog):
    caplog.set_level(logging.WARNING)
    with respx.mock(assert_all_called=True) as router:
        router.post("https://frontend.test/api/revalidate").mock(
            side_effect=httpx.ConnectTimeout("simulated timeout")
        )
        await revalidate_share_slug("abc123")
    assert any("share.revalidate_failed" in r.message for r in caplog.records)


async def test_tag_is_always_share_prefixed(_configured):
    """Even if a future caller passes weirdness, the tag is share:<slug>."""
    with respx.mock(assert_all_called=True) as router:
        route = router.post("https://frontend.test/api/revalidate").mock(
            return_value=httpx.Response(204)
        )
        await revalidate_share_slug("anything-goes-here_123")
    body = _json.loads(route.calls[0].request.content)
    assert body["tag"] == "share:anything-goes-here_123"
