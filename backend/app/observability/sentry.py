"""Sentry init + PII scrub hook for the FastAPI backend.

Scrubbing happens in `before_send`. The full PII contract lives in the v0.8.0
design spec §6. Anything new added there must be added here too — this is the
single point where PII can leak out of the process.
"""
from __future__ import annotations

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

_SCRUB_HEADER_NAMES = {"cookie", "set-cookie", "authorization", "x-vercel-id"}
_SCRUB_EXTRA_KEYS = {
    "access_token",
    "access_token_ct",
    "oauth_state",
    "oauth_code",
    "session_id",
    "email",
}


def _scrub_headers(headers: dict[str, Any] | None) -> dict[str, Any]:
    if not headers:
        return headers or {}
    return {k: v for k, v in headers.items() if k.lower() not in _SCRUB_HEADER_NAMES}


def _scrub_dict_recursive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: _scrub_dict_recursive(v)
            for k, v in value.items()
            if k not in _SCRUB_EXTRA_KEYS and k.lower() not in _SCRUB_HEADER_NAMES
        }
    if isinstance(value, list):
        return [_scrub_dict_recursive(v) for v in value]
    return value


def scrub_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """`before_send` hook — strips known PII from the outgoing event.

    Tolerates missing sections (real events vary in shape). Recursive on
    `extra` / `contexts` because tokens sometimes nest one level deep when a
    library auto-captures local variables.
    """
    request = event.get("request")
    if isinstance(request, dict):
        request["headers"] = _scrub_headers(request.get("headers"))

    user = event.get("user")
    if isinstance(user, dict) and "email" in user:
        del user["email"]

    for section in ("extra", "contexts"):
        bucket = event.get(section)
        if isinstance(bucket, dict):
            event[section] = _scrub_dict_recursive(bucket)

    return event


def init_sentry(
    *,
    dsn: str | None,
    environment: str,
    traces_sample_rate: float,
    release: str,
) -> None:
    """Initialise the Sentry SDK. No-op when DSN is unset OR already initialised.

    Calling `sentry_sdk.init` twice creates a new client and orphans the first
    without flushing — guard against that explicitly so test runs that import
    this module multiple times don't drop events.
    """
    if not dsn:
        logging.getLogger(__name__).info("sentry: DSN unset, skipping init")
        return

    if sentry_sdk.is_initialized():
        logging.getLogger(__name__).warning("sentry: already initialised, skipping re-init")
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        before_send=scrub_event,
        integrations=[
            FastApiIntegration(),
            AsyncPGIntegration(),
            HttpxIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
