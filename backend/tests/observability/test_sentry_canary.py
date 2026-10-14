"""No cookie, secret, token, IP or OAuth value reaches Sentry, end to end.

A real client, configured by init_sentry, captures to an in-memory transport
while a signed-in request carrying canary values fails inside the real app.
Every captured error and transaction is searched for every canary.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import sentry_sdk
from sentry_sdk.transport import Transport

from app import dependencies, ratelimit
from app.auth.dependencies import optional_session
from app.cache.client import RedisCache
from app.main import app
from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo
from app.narrative.budget import DailyBudget
from app.narrative.cache import NarrativeCache
from app.narrative.service import NarrativeService
from app.observability.sentry import init_sentry

if TYPE_CHECKING:
    from collections.abc import Iterator

_CANARIES = {
    "session cookie": "canary-session-7f3a",
    "posthog cookie": "canary-posthog-7f3a",
    "internal secret": "canary-internal-7f3a",
    "cron bearer": "canary-cron-7f3a",
    "oidc token": "canary-oidc-7f3a",
    "visitor ip": "203.0.113.77",
    "vercel visitor ip": "203.0.113.78",
    "city": "canary-city-7f3a",
    "oauth code": "canary-code-7f3a",
    "oauth state": "canary-state-7f3a",
}


@pytest.fixture
def sentry_items(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[str, dict[str, Any]]]]:
    items: list[tuple[str, dict[str, Any]]] = []

    class MemoryTransport(Transport):
        def capture_envelope(self, envelope: Any) -> None:
            items.extend(
                (item.type, item.payload.json)
                for item in envelope.items
                if item.type in ("event", "transaction")
            )

    real_init = sentry_sdk.init
    monkeypatch.setattr(
        sentry_sdk, "init", lambda **options: real_init(transport=MemoryTransport, **options)
    )
    init_sentry(
        dsn="https://key@o1.ingest.sentry.io/1",
        environment="test",
        traces_sample_rate=1.0,
        release="test",
    )
    yield items
    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(None)


async def _route_fails() -> None:
    raise RuntimeError("route failed")


async def test_a_failing_signed_in_request_leaks_no_canary(sentry_items) -> None:
    app.dependency_overrides[optional_session] = _route_fails
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.get(
                f"/me?mode=roast&code={_CANARIES['oauth code']}&state={_CANARIES['oauth state']}",
                headers={
                    "cookie": (
                        f"si_session={_CANARIES['session cookie']}; "
                        f"ph_phc_test_posthog={_CANARIES['posthog cookie']}"
                    ),
                    "x-internal-secret": _CANARIES["internal secret"],
                    "authorization": f"Bearer {_CANARIES['cron bearer']}",
                    "x-vercel-oidc-token": _CANARIES["oidc token"],
                    "x-forwarded-for": _CANARIES["visitor ip"],
                    "x-vercel-forwarded-for": _CANARIES["vercel visitor ip"],
                    "x-vercel-ip-city": _CANARIES["city"],
                    "user-agent": "canary-test-agent",
                },
            )
    finally:
        app.dependency_overrides.pop(optional_session, None)
    sentry_sdk.flush()

    assert response.status_code == 500
    assert {kind for kind, _ in sentry_items} >= {"event", "transaction"}
    for kind, payload in sentry_items:
        text = json.dumps(payload)
        leaked = [name for name, value in _CANARIES.items() if value in text]
        assert leaked == [], f"{kind} leaked: {leaked}"
    error = next(payload for kind, payload in sentry_items if kind == "event")
    headers = {name.lower(): value for name, value in error["request"]["headers"].items()}
    assert headers["user-agent"] == "canary-test-agent"  # still debuggable


_VISITOR_IP = "198.51.100.23"


class _UpstashDown:
    """Every Upstash call fails, as in a quota or network outage."""

    async def get(self, key: str) -> None:
        raise ConnectionError("upstash unreachable")

    async def set(self, key: str, value: str, *, ex: int | None = None, nx: bool = False) -> None:
        raise ConnectionError("upstash unreachable")

    async def delete(self, *keys: str) -> None:
        raise ConnectionError("upstash unreachable")

    async def incr(self, key: str) -> None:
        raise ConnectionError("upstash unreachable")

    async def decr(self, key: str) -> None:
        raise ConnectionError("upstash unreachable")

    async def expire(self, key: str, seconds: int) -> None:
        raise ConnectionError("upstash unreachable")

    async def ping(self) -> None:
        raise ConnectionError("upstash unreachable")


class _FailingProvider:
    async def stream_chat(self, messages: Any, **kwargs: Any) -> Any:
        raise RuntimeError("provider returned 503")
        yield  # pragma: no cover - makes this an async generator


def _report() -> Report:
    zero = ScoreResult(points=0, max_points=1)
    return Report(
        username="octo",
        tier=TierInfo(name="Professional Developer", sub_rank=50, band=(50, 65)),
        breakdown=ScoreBreakdown(
            repo_quality=zero,
            engineering_maturity=zero,
            oss_collab=zero,
            consistency=zero,
            recruiter_signal=zero,
            learning_trajectory=zero,
        ),
        total=50,
        generated_at=datetime.now(UTC),
    )


async def test_a_cache_outage_puts_no_visitor_ip_in_the_narrative_alert(
    sentry_items, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rate-limit and budget keys embed an anonymous caller's IP. With Upstash
    down, every cache call logs its key, each log line becomes a breadcrumb,
    and the narrative-outage alert captured in the same request carries them."""
    cache = RedisCache(_UpstashDown())
    monkeypatch.setattr(ratelimit, "get_cache", lambda: cache)

    async def report_for(username: str) -> Report:
        return _report()

    def failing_narrator() -> NarrativeService:
        return NarrativeService(
            cache=NarrativeCache(redis=cache),
            budget=DailyBudget(limit=10, redis=cache),
            llm=_FailingProvider(),
        )

    app.dependency_overrides[dependencies.get_report_for_user] = report_for
    app.dependency_overrides[dependencies.get_narrative_service] = failing_narrator
    header = ratelimit.settings_module.settings.trusted_client_ip_header
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            await client.get(
                "/narrative/octo?mode=roast",
                headers={header: _VISITOR_IP, "user-agent": "canary-test-agent"},
            )
    finally:
        app.dependency_overrides.pop(dependencies.get_report_for_user, None)
        app.dependency_overrides.pop(dependencies.get_narrative_service, None)
    sentry_sdk.flush()

    events = [payload for kind, payload in sentry_items if kind == "event"]
    assert any((event.get("fingerprint") or [None])[0] == "narrative-fallback" for event in events)
    leaked = [kind for kind, payload in sentry_items if _VISITOR_IP in json.dumps(payload)]
    assert leaked == []
