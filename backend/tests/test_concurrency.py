import asyncio

import httpx
import pytest

from app.concurrency import gather_all


@pytest.mark.asyncio
async def test_gather_all_cancels_the_rest_when_one_fails() -> None:
    """A failed analysis must not leave sibling GitHub calls running against a
    client that is about to close."""
    slow_was_cancelled = asyncio.Event()

    async def fails_fast() -> None:
        raise httpx.ConnectError("boom")

    async def slow() -> None:
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            slow_was_cancelled.set()
            raise

    with pytest.raises(httpx.ConnectError):
        await gather_all(slow(), fails_fast())
    assert slow_was_cancelled.is_set()


@pytest.mark.asyncio
async def test_gather_all_keeps_argument_order() -> None:
    async def after(delay: float, value: str) -> str:
        await asyncio.sleep(delay)
        return value

    assert await gather_all(after(0.02, "first"), after(0, "second")) == ["first", "second"]
