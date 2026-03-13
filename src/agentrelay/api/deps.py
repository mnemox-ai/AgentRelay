"""FastAPI dependencies."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.db import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session and commit on success / rollback on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
