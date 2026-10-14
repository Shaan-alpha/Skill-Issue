"""Sentry init + PII scrub hook for the FastAPI backend.

The PII contract lives in docs/OBSERVABILITY.md ("PII contract"). Scrubbing
happens in `scrub_event`, which runs on errors (`before_send`) and on
transactions (`before_send_transaction`). The contract lists mirror
frontend/src/observability/scrub.ts; tests/observability/test_scrub_drift.py
fails if the two diverge.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import sentry_sdk
from sentry_sdk.integrations import DidNotEnable, Integration
from sentry_sdk.integrations.asyncpg import AsyncPGIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

if TYPE_CHECKING:
    from collections.abc import Callable

# Request headers that may reach Sentry; every other header is dropped.
_HEADER_ALLOWLIST = ["user-agent", "referer", "content-type", "accept", "host"]
# A query parameter whose name contains one of these keeps its name, and its
# value becomes [Filtered]: OAuth code and state, tokens, keys, sessions.
_QUERY_DENY_TERMS = [
    "code",
    "state",
    "token",
    "key",
    "secret",
    "session",
    "sid",
    "passw",
    "pwd",
    "credential",
    "csrf",
    "xsrf",
    "jwt",
    "bearer",
]
_FILTERED = "[Filtered]"

# Header-like keys dropped wherever they appear in `extra` and `contexts`
# (request headers themselves go through the allow-list above).
_SCRUB_HEADER_NAMES = {
    "cookie",
    "set-cookie",
    "authorization",
    "x-vercel-id",
    "x-internal-secret",
    "x-revalidate-secret",
    "x-client-ip",
    "x-forwarded-for",
    "x-real-ip",
}
_SCRUB_EXTRA_KEYS = {
    "access_token",
    "access_token_ct",
    "oauth_state",
    "oauth_code",
    "session_id",
    "email",
}

_ALLOWED_HEADERS = frozenset(_HEADER_ALLOWLIST)
# Span attributes carry headers as http.request.header.user_agent and so on.
_ALLOWED_SPAN_HEADER_KEYS = frozenset(
    f"http.{direction}.header.{name.replace('-', '_')}"
    for direction in ("request", "response")
    for name in _HEADER_ALLOWLIST
)
_URL_DATA_KEYS = frozenset({"http.target", "http.url", "url.full", "url"})
_QUERY_DATA_KEYS = frozenset({"url.query", "http.query"})


def _sensitive_param(name: str) -> bool:
    lowered = name.lower()
    return any(term in lowered for term in _QUERY_DENY_TERMS)


def _filter_query(query: str) -> str:
    """Blank the values of sensitive parameters. A plain split, never URL
    encoding, so the result matches the frontend's byte for byte."""
    prefix = "?" if query.startswith("?") else ""
    pairs = []
    for pair in query[len(prefix) :].split("&"):
        name, sep, _value = pair.partition("=")
        pairs.append(f"{name}={_FILTERED}" if sep and _sensitive_param(name) else pair)
    return prefix + "&".join(pairs)


def _filter_url(url: str) -> str:
    """Filter the query part of a URL or path; the rest is untouched."""
    base, sep, rest = url.partition("?")
    if not sep:
        return url
    query, hash_sep, fragment = rest.partition("#")
    return f"{base}?{_filter_query(query)}{hash_sep}{fragment}"


def _replace(owner: dict[str, Any], key: str, scrub: Callable[[Any], Any]) -> None:
    """Replace owner[key] with its scrubbed value, or drop it if scrubbing
    fails. Fails closed: a part we can't read is a part we don't send. The
    hook itself must never raise, because the SDK would drop the whole event,
    alert events included."""
    if key not in owner:
        return
    try:
        owner[key] = scrub(owner[key])
    except Exception:
        owner.pop(key, None)


def _allowed_headers(headers: Any) -> dict[str, Any]:
    if not isinstance(headers, dict):
        raise TypeError("request headers")
    out: dict[str, Any] = {}
    for name, value in headers.items():
        lowered = str(name).lower()
        if lowered not in _ALLOWED_HEADERS:
            continue
        out[name] = _filter_url(value) if lowered == "referer" and isinstance(value, str) else value
    return out


def _filtered_query_string(value: Any) -> Any:
    if isinstance(value, str):
        return _filter_query(value)
    if isinstance(value, dict):
        return {k: _FILTERED if _sensitive_param(str(k)) else v for k, v in value.items()}
    if isinstance(value, list):
        return [
            [pair[0], _FILTERED]
            if isinstance(pair, list | tuple) and len(pair) == 2 and _sensitive_param(str(pair[0]))
            else pair
            for pair in value
        ]
    raise TypeError("query_string")


def _filtered_url_value(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("url")
    return _filter_url(value)


def _scrub_request(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise TypeError("request")
    for key in ("cookies", "data", "env"):
        request.pop(key, None)
    _replace(request, "headers", _allowed_headers)
    _replace(request, "query_string", _filtered_query_string)
    _replace(request, "url", _filtered_url_value)
    return request


def _scrub_user(user: Any) -> dict[str, Any]:
    if not isinstance(user, dict):
        raise TypeError("user")
    user.pop("ip_address", None)
    user.pop("email", None)
    return user


def _scrubbed_span_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError("span data")
    out: dict[str, Any] = {}
    for key, value in data.items():
        if key.startswith(("http.request.header.", "http.response.header.")):
            if key in _ALLOWED_SPAN_HEADER_KEYS:
                referer = key.endswith(".referer") and isinstance(value, str)
                out[key] = _filter_url(value) if referer else value
        elif key == "http.request.body.data":
            continue
        elif key in _URL_DATA_KEYS and isinstance(value, str):
            out[key] = _filter_url(value)
        elif key in _QUERY_DATA_KEYS and isinstance(value, str):
            out[key] = _filter_query(value)
        else:
            out[key] = value
    return out


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


def _scrub_contexts(contexts: Any) -> dict[str, Any]:
    if not isinstance(contexts, dict):
        raise TypeError("contexts")
    trace = contexts.get("trace")
    if isinstance(trace, dict):
        _replace(trace, "data", _scrubbed_span_data)
    return _scrub_dict_recursive(contexts)


def _scrub_spans(spans: Any) -> list[Any]:
    if not isinstance(spans, list):
        raise TypeError("spans")
    for span in spans:
        if isinstance(span, dict):
            _replace(span, "data", _scrubbed_span_data)
    return spans


def _scrubbed_breadcrumb_data(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise TypeError("breadcrumb data")
    for key in ("url", "from", "to"):
        if isinstance(data.get(key), str):
            data[key] = _filter_url(data[key])
    if isinstance(data.get("http.query"), str):
        data["http.query"] = _filter_query(data["http.query"])
    return data


def _scrub_breadcrumbs(breadcrumbs: Any) -> Any:
    # Serialized events hold {"values": [...]}; accept a bare list too.
    values = breadcrumbs.get("values") if isinstance(breadcrumbs, dict) else breadcrumbs
    if not isinstance(values, list):
        raise TypeError("breadcrumbs")
    for crumb in values:
        if isinstance(crumb, dict):
            _replace(crumb, "data", _scrubbed_breadcrumb_data)
    return breadcrumbs


def scrub_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """`before_send` and `before_send_transaction`: enforces the PII contract
    on every error and transaction. Each part is scrubbed on its own and
    dropped if it can't be."""
    _replace(event, "request", _scrub_request)
    _replace(event, "user", _scrub_user)
    _replace(event, "contexts", _scrub_contexts)
    _replace(event, "spans", _scrub_spans)
    _replace(event, "breadcrumbs", _scrub_breadcrumbs)
    _replace(event, "extra", _scrub_dict_recursive)
    return event


def _disabled_integrations() -> list[Integration]:
    """Sentry's OpenAI integration, which is auto-enabled because openai is
    installed. It reports every provider failure as unhandled, though the
    narrator falls back, and the dedupe integration then drops the
    fingerprinted event the narrative-outage alert matches. Provider calls
    still show up as httpx spans.

    Imported here, defensively: it raises at import when openai is missing or
    reorganised, and telemetry must never stop the app from starting. Then
    there is nothing to turn off.
    """
    try:
        from sentry_sdk.integrations.openai import OpenAIIntegration
    except (ImportError, DidNotEnable):
        return []
    return [OpenAIIntegration()]


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

    # The PII contract (docs/OBSERVABILITY.md): no frame locals, no request
    # bodies, and the same scrub on transactions as on errors. Still no
    # send_default_pii or data_collection: send_default_pii is deprecated
    # (2.72) even as False, and passing data_collection opts into the SDK's
    # permissive defaults and drops its EventScrubber.
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        include_local_variables=False,
        max_request_body_size="never",
        before_send=scrub_event,
        before_send_transaction=scrub_event,
        integrations=[
            FastApiIntegration(),
            AsyncPGIntegration(),
            HttpxIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
        disabled_integrations=_disabled_integrations(),
    )
