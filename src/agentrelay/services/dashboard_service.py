"""Dashboard service — aggregated stats for the frontend."""

from __future__ import annotations

import uuid

from agentrelay.repositories.dashboard_repo import DashboardRepository
from agentrelay.schemas.dashboard import (
    DashboardStats,
    LedgerEntryResponse,
    RecentTask,
    TopAgent,
    ValidationRate,
)


class DashboardService:
    def __init__(self, repo: DashboardRepository) -> None:
        self.repo = repo

    async def get_stats(self) -> DashboardStats:
        data = await self.repo.get_stats()
        return DashboardStats(**data)

    async def get_recent_tasks(self) -> list[RecentTask]:
        rows = await self.repo.get_recent_tasks()
        return [RecentTask(**row) for row in rows]

    async def get_top_agents(self) -> list[TopAgent]:
        rows = await self.repo.get_top_agents()
        return [TopAgent(**row) for row in rows]

    async def get_validation_rate(self) -> ValidationRate:
        data = await self.repo.get_validation_rate()
        return ValidationRate(**data)

    async def get_agent_ledger(self, agent_id: uuid.UUID) -> list[LedgerEntryResponse]:
        """Returns ledger entries or raises ValueError if agent not found."""
        result = await self.repo.get_agent_ledger(agent_id)
        if result is None:
            raise ValueError("Agent not found")
        return result

    async def get_agent_reputation(self, agent_id: uuid.UUID):
        """Returns reputation snapshot or raises ValueError."""
        result = await self.repo.get_agent_reputation(agent_id)
        if result == "agent_not_found":
            raise ValueError("Agent not found")
        if result is None:
            raise ValueError("No reputation data for this agent")
        return result
