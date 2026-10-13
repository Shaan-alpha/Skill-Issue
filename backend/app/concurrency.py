from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable


async def gather_all[T](*aws: Awaitable[T]) -> list[T]:
    """`asyncio.gather` that cancels the rest as soon as one awaitable fails.

    Plain gather leaves the siblings running after a failure: they keep calling
    GitHub for an analysis that has already failed, then hit the closed client
    and log "Task exception was never retrieved".
    """
    tasks = [asyncio.ensure_future(aw) for aw in aws]
    try:
        return await asyncio.gather(*tasks)
    except BaseException:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
