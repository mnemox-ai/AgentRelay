"""Async CRUD repository for ReputationSnapshot model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.models.reputation import ReputationSnapshot


class ReputationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_snapshot(self, **kwargs) -> ReputationSnapshot:
        # Set snapshot_at explicitly with microsecond precision to avoid
        # non-deterministic ordering when server_default resolves to the same second.
        if "snapshot_at" not in kwargs:
            kwargs["snapshot_at"] = datetime.now(timezone.utc)
        snapshot = ReputationSnapshot(**kwargs)
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_latest(self, agent_id: uuid.UUID) -> ReputationSnapshot | None:
        stmt = (
            select(ReputationSnapshot)
            .where(ReputationSnapshot.agent_id == agent_id)
            .order_by(ReputationSnapshot.snapshot_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
