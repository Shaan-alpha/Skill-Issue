"""No cookie, secret, token, IP or OAuth value reaches Sentry, end to end.

A real client, configured by init_sentry, captures to an in-memory transport
while a signed-in request carrying canary values fails inside the real app.
Every captured error and transaction is searched for every canary.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import sentry_sdk
from sentry_sdk.transport import Transport

from app.auth.dependencies import optional_session
from app.main import app
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
