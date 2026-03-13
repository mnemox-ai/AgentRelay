"""API key generation and verification."""

from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.models.agent import Agent


def generate_api_key() -> str:
    """Generate a 64-character hex API key."""
    return secrets.token_hex(32)


async def verify_api_key(key: str, db: AsyncSession) -> Agent | None:
    """Look up an agent by API key. Returns the Agent or None."""
    stmt = select(Agent).where(Agent.api_key == key)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
