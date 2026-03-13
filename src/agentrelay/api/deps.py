"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.db import async_session_factory
from agentrelay.models.agent import Agent
from agentrelay.security.auth import verify_api_key


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session and commit on success / rollback on error."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_current_agent(
    x_api_key: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """Authenticate via X-API-Key header. Returns the Agent or raises 401."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")
    agent = await verify_api_key(x_api_key, db)
    if agent is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return agent
