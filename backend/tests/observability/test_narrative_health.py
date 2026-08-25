"""The signal that would have caught the 2026-08-16 model retirement on day one.

A narrative that degrades to stand-in text looks identical from the outside
whether the daily cap was hit (expected) or the provider rejected us (an
incident). These tests pin the distinction.
"""

from unittest.mock import patch

from app.observability.narrative_health import record_narrative_fallback


def test_upstream_error_is_captured_as_a_sentry_event() -> None:
    with patch("app.observability.narrative_health.sentry_sdk") as sdk:
        record_narrative_fallback(reason="error", mode="roast", username="octocat")

    assert sdk.capture_message.call_count == 1
    _args, kwargs = sdk.capture_message.call_args
    assert kwargs["level"] == "error"


def test_budget_exhaustion_is_not_captured_as_an_error() -> None:
    """Hitting the daily cap is capacity behaviour, not an incident. Paging on
    it would train the operator to ignore the alert that matters."""
    with patch("app.observability.narrative_health.sentry_sdk") as sdk:
        record_narrative_fallback(reason="budget", mode="roast", username="octocat")

    assert sdk.capture_message.call_count == 0


def test_error_events_share_one_fingerprint_so_they_group() -> None:
    """All upstream fallbacks must collapse into a single alertable issue
    rather than scattering by message text."""
    with patch("app.observability.narrative_health.sentry_sdk") as sdk:
        record_narrative_fallback(reason="error", mode="roast", username="a")
        record_narrative_fallback(reason="error", mode="mentor", username="b")

    fingerprints = [c.kwargs["fingerprint"] for c in sdk.capture_message.call_args_list]
    assert fingerprints[0] == fingerprints[1]
    assert fingerprints[0] == ["narrative-fallback", "error"]


def test_mode_and_reason_are_tagged_for_filtering() -> None:
    with patch("app.observability.narrative_health.sentry_sdk") as sdk:
        scope = sdk.new_scope.return_value.__enter__.return_value
        record_narrative_fallback(reason="error", mode="mentor", username="octocat")

    tagged = {c.args[0]: c.args[1] for c in scope.set_tag.call_args_list}
    assert tagged["narrative.fallback_reason"] == "error"
    assert tagged["narrative.mode"] == "mentor"


def test_username_is_context_not_a_tag() -> None:
    """Usernames are unbounded — as a tag they would blow out Sentry's
    cardinality limits and make the issue unsearchable."""
    with patch("app.observability.narrative_health.sentry_sdk") as sdk:
        scope = sdk.new_scope.return_value.__enter__.return_value
        record_narrative_fallback(reason="error", mode="roast", username="octocat")

    tag_names = {c.args[0] for c in scope.set_tag.call_args_list}
    assert not any("username" in t for t in tag_names)
    assert scope.set_context.called


def test_never_raises_when_sentry_is_uninitialised() -> None:
    """Telemetry fails open — a reporting failure must never take down the
    narrative it is reporting on."""
    with patch("app.observability.narrative_health.sentry_sdk") as sdk:
        sdk.new_scope.side_effect = RuntimeError("sentry exploded")
        record_narrative_fallback(reason="error", mode="roast", username="octocat")
