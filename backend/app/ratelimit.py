from __future__ import annotations

import hmac
import logging
from typing import TYPE_CHECKING

from app import settings as settings_module

if TYPE_CHECKING:
    from datetime import datetime

    from fastapi import Request

logger = logging.getLogger(__name__)


def hour_bucket(now: datetime) -> str:
    return now.strftime("%Y-%m-%d-%H")


def seconds_until_next_hour(now: datetime) -> int:
    next_hour = now.replace(minute=0, second=0, microsecond=0).timestamp() + 3600
    return max(1, int(next_hour - now.timestamp()))


def client_ip(request: Request, *, trusted_proxy: bool) -> str:
    """Resolve the caller's IP.

    When `trusted_proxy` (the X-Internal-Secret matched), trust the RSC-forwarded
    `X-Client-IP`. Otherwise use Vercel's `x-real-ip`, then the leftmost
    `x-forwarded-for` hop, then the raw connection host.
    """
    headers = request.headers
    if trusted_proxy:
        forwarded = headers.get("x-client-ip")
        if forwarded and forwarded.strip():
            return forwarded.strip()
    real = headers.get("x-real-ip")
    if real and real.strip():
        return real.strip()
    xff = headers.get("x-forwarded-for")
    if xff:
        first = xff.split(",")[0].strip()
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
