"""Alertable signal for a narrative that degraded to stand-in text.

The narrative layer is deliberately fail-soft: any provider failure becomes
on-voice fallback prose rather than a 5xx. That is right for the reader and
wrong for the operator — when Groq retired `llama-3.3-70b-versatile` on
2026-08-16 the site served stand-in text for three days with green health
checks and no page.

Errors did reach Sentry, but only incidentally, as whatever exception happened
to raise. This module makes the degradation itself the signal: one stable
fingerprint covering every upstream fallback, so it can carry an alert rule of
its own. Budget exhaustion is deliberately excluded — it is expected capacity
behaviour, and paging on it would train the operator to ignore the alert that
matters.
"""

from __future__ import annotations

import logging
from typing import Literal

import sentry_sdk

logger = logging.getLogger(__name__)

Reason = Literal["budget", "error"]

# Every upstream fallback groups into one Sentry issue, regardless of mode or
# message wording, so a single alert rule covers the whole failure class.
_ERROR_FINGERPRINT = ["narrative-fallback", "error"]


def record_narrative_fallback(
    *,
    reason: Reason,
    mode: str,
    username: str,
    detail: str | None = None,
) -> None:
    """Record that a narrative fell back to stand-in text.

    `reason="budget"` logs a warning and stops: the daily cap is a designed
    limit, not an incident. `reason="error"` additionally captures a Sentry
    event so the degradation is alertable on its own.

    Telemetry fails open. A failure to report must never take down the request
    it is reporting on.
    """
    if reason == "budget":
        logger.warning("narrative.fallback reason=budget mode=%s user=%s", mode, username)
        return

    logger.error(
        "narrative.fallback reason=error mode=%s user=%s detail=%s", mode, username, detail
    )

    try:
        with sentry_sdk.new_scope() as scope:
            # Low-cardinality only: usernames as tags would exhaust Sentry's
            # tag-value limits and make the issue unsearchable.
            scope.set_tag("narrative.fallback_reason", "error")
            scope.set_tag("narrative.mode", mode)
            scope.set_context(
                "narrative",
                {"username": username, "mode": mode, "detail": detail},
            )
            sentry_sdk.capture_message(
                "Narrative degraded to fallback text (upstream failure)",
                level="error",
                fingerprint=_ERROR_FINGERPRINT,
            )
    except Exception:  # pragma: no cover - defensive; telemetry never breaks a request
        logger.exception("narrative.fallback: failed to report to Sentry")
