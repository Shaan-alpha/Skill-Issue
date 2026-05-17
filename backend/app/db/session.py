from collections.abc import AsyncIterator

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
