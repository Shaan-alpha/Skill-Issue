"""One narrative outage, one alertable Sentry event, checked end to end.

test_narrative_health.py mocks the Sentry SDK, so it cannot see what the SDK
itself does with an event. Here a real client, configured by init_sentry,
sends to an in-memory transport while the real narrator fails against a mocked
provider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import httpx
import pytest
import respx
import sentry_sdk
from sentry_sdk.transport import Transport

from app.models import Report, ScoreBreakdown, ScoreResult, TierInfo
from app.narrative.budget import DailyBudget
from app.narrative.cache import NarrativeCache
from app.narrative.llm import NarrativeLLM
from app.narrative.service import NarrativeService
from app.observability.sentry import init_sentry

if TYPE_CHECKING:
    from collections.abc import Iterator

_PROVIDER = "https://provider.test/v1"


@pytest.fixture
def sentry_events(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []

    class MemoryTransport(Transport):
        def capture_envelope(self, envelope: Any) -> None:
            events.extend(item.payload.json for item in envelope.items if item.type == "event")

    real_init = sentry_sdk.init
    monkeypatch.setattr(
        sentry_sdk, "init", lambda **options: real_init(transport=MemoryTransport, **options)
    )
    init_sentry(
        dsn="https://key@o1.ingest.sentry.io/1",
        environment="test",
        traces_sample_rate=0.0,
        release="test",
    )
    yield events
    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(None)


def _report() -> Report:
    z = ScoreResult(points=0, max_points=1)
    return Report(
        username="octo",
        tier=TierInfo(name="Professional Developer", sub_rank=50, band=(50, 65)),
        breakdown=ScoreBreakdown(
            repo_quality=z,
            engineering_maturity=z,
            oss_collab=z,
            consistency=z,
            recruiter_signal=z,
            learning_trajectory=z,
        ),
        total=50,
        generated_at=datetime.now(UTC),
    )


@respx.mock
async def test_a_provider_failure_raises_one_event_carrying_the_alert_fingerprint(
    sentry_events: list[dict[str, Any]],
) -> None:
    """The 2026-08-16 incident again: the provider retires the model. The alert
    rule matches the narrative-fallback fingerprint, so that event must be the
    one that reaches Sentry, carrying the provider's exception."""
    respx.post(f"{_PROVIDER}/chat/completions").mock(
        return_value=httpx.Response(
            400,
            json={
                "error": {
                    "message": "The model has been decommissioned",
                    "type": "invalid_request_error",
                    "code": "model_decommissioned",
                }
            },
        )
    )
    service = NarrativeService(
        cache=NarrativeCache(),
        budget=DailyBudget(limit=100),
        llm=NarrativeLLM(api_key="test", model="retired-model", base_url=_PROVIDER),
    )

    chunks = [chunk async for chunk in service.stream_narrative("roast", _report())]

    assert chunks, "the reader still gets the stand-in narrative"
    assert [event.get("fingerprint") for event in sentry_events] == [
        ["narrative-fallback", "error"]
    ]
    (event,) = sentry_events
    assert event["exception"]["values"][-1]["type"] == "BadRequestError"
    assert event["contexts"]["narrative"]["mode"] == "roast"
