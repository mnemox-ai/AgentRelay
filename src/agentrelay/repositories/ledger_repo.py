"""Async CRUD repository for LedgerEntry model."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from agentrelay.models.ledger import LedgerEntry


class LedgerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs) -> LedgerEntry:
        entry = LedgerEntry(**kwargs)
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_balance(self, agent_id: uuid.UUID) -> float:
        stmt = select(func.coalesce(func.sum(LedgerEntry.amount), 0.0)).where(
            LedgerEntry.agent_id == agent_id
        )
        result = await self.session.execute(stmt)
        return float(result.scalar_one())
