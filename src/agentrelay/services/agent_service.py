"""Agent service — registration and lookup."""

from __future__ import annotations

import uuid

from agentrelay.models.agent import Agent
from agentrelay.repositories.agent_repo import AgentRepository
from agentrelay.schemas.agent import AgentRegister
from agentrelay.security.auth import generate_api_key


class AgentService:
    def __init__(self, agent_repo: AgentRepository) -> None:
        self.agent_repo = agent_repo

    async def register_agent(self, data: AgentRegister) -> Agent:
        """Register a new agent. Raises ValueError if name already taken."""
        existing = await self.agent_repo.get_by_name(data.name)
        if existing is not None:
            raise ValueError("Agent name already registered")
        api_key = generate_api_key()
        return await self.agent_repo.create(
            name=data.name,
            api_key=api_key,
            quota_profile=data.quota_profile,
            capabilities=data.capabilities,
        )

    async def get_agent(self, agent_id: uuid.UUID) -> Agent:
        """Get agent by ID. Raises ValueError if not found."""
        agent = await self.agent_repo.get(agent_id)
        if agent is None:
            raise ValueError("Agent not found")
        return agent
