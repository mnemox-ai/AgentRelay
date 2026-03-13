"""Ledger service — record rewards and penalties for agents."""

from __future__ import annotations

import uuid

from agentrelay.models.ledger import LedgerEntry
from agentrelay.repositories.ledger_repo import LedgerRepository


class LedgerService:
    def __init__(self, ledger_repo: LedgerRepository) -> None:
        self.ledger_repo = ledger_repo

    async def record_reward(
        self, agent_id: uuid.UUID, task_id: uuid.UUID, amount: float
    ) -> LedgerEntry:
        return await self.ledger_repo.create(
            agent_id=agent_id,
            task_id=task_id,
            amount=amount,
            entry_type="reward",
        )

    async def record_penalty(
        self, agent_id: uuid.UUID, task_id: uuid.UUID, amount: float
    ) -> LedgerEntry:
        return await self.ledger_repo.create(
            agent_id=agent_id,
            task_id=task_id,
            amount=-abs(amount),
            entry_type="penalty",
        )

    async def get_balance(self, agent_id: uuid.UUID) -> float:
        return await self.ledger_repo.get_balance(agent_id)
