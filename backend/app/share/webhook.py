"""Backend → frontend webhook that busts Next.js cache tags after a
share toggle.

Fire-and-forget: failure to invalidate is logged (and Sentry catches the
exception via the logging integration when severity is high enough), but
never raises into the caller. Graceful degradation: with the env vars
unset (local dev, partial deploys) the call is a no-op and the frontend's
`cacheLife({ revalidate: 3600 })` fallback absorbs the gap.
"""

from __future__ import annotations

import logging

import httpx

from app import settings as settings_module

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 5.0


async def revalidate_share_slug(slug: str) -> None:
    """POST {FRONTEND_BASE_URL}/api/revalidate with the slug's cache tag.

    Reads through `settings_module.settings` (not a `from .. import` binding)
    so tests that reassign the singleton are seen at call time.
    """
    cfg = settings_module.settings
    if not cfg.frontend_base_url or not cfg.revalidate_secret:
        logger.warning("share.revalidate_skipped slug=%s reason=unconfigured", slug)
        return

    url = f"{cfg.frontend_base_url.rstrip('/')}/api/revalidate"
    body = {"tag": f"share:{slug}"}
    headers = {
        "Content-Type": "application/json",
        "X-Revalidate-Secret": cfg.revalidate_secret,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=body, headers=headers)
        if resp.status_code >= 400:
            logger.warning(
                "share.revalidate_failed slug=%s status=%s body=%s",
                slug,
                resp.status_code,
                resp.text[:200],
            )
            return
        logger.info("share.revalidate_succeeded slug=%s", slug)
    except (httpx.HTTPError, OSError) as exc:
        logger.warning("share.revalidate_failed slug=%s error=%s", slug, exc)
