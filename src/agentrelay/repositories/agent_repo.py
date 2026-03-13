"""Async CRUD repository for Agent model."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.models.agent import Agent


class AgentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs) -> Agent:
        agent = Agent(**kwargs)
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def get(self, agent_id: uuid.UUID) -> Agent | None:
        return await self.session.get(Agent, agent_id)

    async def get_by_name(self, name: str) -> Agent | None:
        stmt = select(Agent).where(Agent.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, agent_id: uuid.UUID, **kwargs) -> Agent | None:
        stmt = update(Agent).where(Agent.id == agent_id).values(**kwargs)
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get(agent_id)
