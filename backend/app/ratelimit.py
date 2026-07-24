from __future__ import annotations

import hmac
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException, Request, status

from app import settings as settings_module
from app.auth.dependencies import optional_session
from app.cache.rate_limit import try_increment_counter
from app.dependencies import get_cache

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


def hour_bucket(now: datetime) -> str:
    return now.strftime("%Y-%m-%d-%H")


def seconds_until_next_hour(now: datetime) -> int:
    next_hour = now.replace(minute=0, second=0, microsecond=0).timestamp() + 3600
    return max(1, int(next_hour - now.timestamp()))


def client_ip(request: Request, *, trusted_proxy: bool) -> str:
    """Resolve the caller's IP.

    When `trusted_proxy` (the X-Internal-Secret matched), trust the RSC-forwarded
    `X-Client-IP`. Otherwise use the configured trusted forwarded header
    (`settings.trusted_client_ip_header`, default `x-forwarded-for`, which Vercel
    OVERWRITES at the edge to prevent spoofing — per
    https://vercel.com/docs/headers/request-headers). `x-real-ip` is NOT trusted:
    Vercel makes no spoof-proofing guarantee for it (v1.0.4 SI-04).
    """
    headers = request.headers
    if trusted_proxy:
        forwarded = headers.get("x-client-ip")
        if forwarded and forwarded.strip():
            return forwarded.strip()
    header_name = settings_module.settings.trusted_client_ip_header
    fwd = headers.get(header_name)
    if fwd:
        first = fwd.split(",")[0].strip()
        if first:
            return first
    if request.client is not None:
        return request.client.host
    return "unknown"


def is_trusted_proxy(request: Request) -> bool:
    """Constant-time compare of X-Internal-Secret against the configured secret.
    False whenever the secret is unset, so a forwarded X-Client-IP is never
    trusted in that mode."""
    secret = settings_module.settings.internal_proxy_secret
    if not secret:
        return False
    provided = request.headers.get("x-internal-secret", "")
    return hmac.compare_digest(provided, secret)


def resolve_budget_subject(request: Request, session: object | None) -> tuple[str, int]:
    """Return (subject, per_subject_daily_limit) for the narrative LLM budget,
    matching the rate limiter's `user:`/`ip:` scheme (v1.0.4 SI-02)."""
    settings = settings_module.settings
    if session is not None:
        return f"user:{session.user.id}", settings.narrative_user_daily_limit
    ip = client_ip(request, trusted_proxy=is_trusted_proxy(request))
    return f"ip:{ip}", settings.narrative_anon_ip_daily_limit


def make_rate_limiter(
    *,
    name: str,
    anon_limit_field: str,
    user_limit_field: str,
    via_trusted_proxy: bool,
) -> Callable[..., Awaitable[None]]:
    """Build a FastAPI dependency that enforces a per-hour cap.

    Signed-in callers are capped per-user (`user:<id>`); anonymous callers
    per-IP (`ip:<addr>`). `via_trusted_proxy=True` (analyze, reached through the
    RSC proxy) skips anonymous enforcement when `internal_proxy_secret` is unset,
    so website visitors aren't collapsed into one Vercel-infra-IP bucket.
    """

    async def _dependency(
        request: Request,
        session: Annotated[object | None, Depends(optional_session)] = None,
    ) -> None:
        cache = get_cache()
        if cache is None:
            return  # cache unconfigured -> fail-open (no limiting)

        settings = settings_module.settings
        if session is not None:
            subject = f"user:{session.user.id}"
            limit = getattr(settings, user_limit_field)
            subject_type = "user"
        else:
            if via_trusted_proxy and not settings.internal_proxy_secret:
                # SI-05: fail CLOSED to a conservative shared backstop instead of
                # skipping. Proxied anon /analyze arrives from the Vercel-infra
                # egress IP, so a shared bucket avoids collapsing real visitors
                # into strict per-IP throttling while still capping total volume.
                logger.warning(
                    "rate_limit.unattributed_backstop name=%s reason=internal_proxy_secret_unset",
                    name,
                )
                subject = "ip:unattributed"
                limit = settings.analyze_unattributed_per_hour
                subject_type = "unattributed"
            else:
                ip = client_ip(request, trusted_proxy=is_trusted_proxy(request))
                subject = f"ip:{ip}"
                limit = getattr(settings, anon_limit_field)
                subject_type = "ip"

        now = datetime.now(UTC)
        result = await try_increment_counter(
            cache,
            name=name,
            subject=subject,
            limit=limit,
            hour_bucket=hour_bucket(now),
        )
        if not result.allowed:
            retry_after = seconds_until_next_hour(now)
            logger.warning(
                "rate_limit.throttled name=%s subject_type=%s limit=%s",
                name,
                subject_type,
                limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"error": "rate_limited", "retry_after_seconds": retry_after},
                headers={"Retry-After": str(retry_after)},
            )

    return _dependency


analyze_rate_limiter = make_rate_limiter(
    name="analyze",
    anon_limit_field="analyze_anon_per_ip_per_hour",
    user_limit_field="analyze_user_per_hour",
    via_trusted_proxy=True,
)

narrative_rate_limiter = make_rate_limiter(
    name="narrative",
    anon_limit_field="narrative_anon_per_ip_per_hour",
    user_limit_field="narrative_user_per_hour",
    via_trusted_proxy=False,
)
