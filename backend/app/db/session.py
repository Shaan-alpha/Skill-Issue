from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import SessionLocal


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped AsyncSession.

    Commits on successful return; rolls back on exception.
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Use this, not a bare Depends(get_db). FastAPI runs a yield dependency's
# teardown after the response is sent unless it is function-scoped, and the
# commit lives in that teardown: without scope="function" a client can act on a
# 2xx before the write exists. Only a streaming route that writes inside its
# stream (and commits explicitly) should take a request-scoped session.
DbSession = Annotated[AsyncSession, Depends(get_db, scope="function")]
