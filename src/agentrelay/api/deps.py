"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.config import settings
from agentrelay.db import async_session_factory
from agentrelay.models.agent import Agent
from agentrelay.security.auth import verify_api_key
from agentrelay.security.rate_limiter import RateLimiter

# Single process-wide rate limiter instance
_rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


def get_rate_limiter() -> RateLimiter:
    """Return the global rate limiter (overridable in tests)."""
    return _rate_limiter


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


async def rate_limit_by_agent(
    response: Response,
    agent: Agent = Depends(get_current_agent),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> Agent:
    """Rate-limit authenticated endpoints using agent_id as key."""
    key = str(agent.id)
    if not limiter.check(key):
        retry = limiter.retry_after(key)
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={"Retry-After": str(retry)},
        )
    return agent


async def rate_limit_by_ip(
    request: Request,
    response: Response,
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    """Rate-limit public endpoints using client IP as key."""
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.check(client_ip):
        retry = limiter.retry_after(client_ip)
        raise HTTPException(
            status_code=429,
            detail="Too Many Requests",
            headers={"Retry-After": str(retry)},
        )
