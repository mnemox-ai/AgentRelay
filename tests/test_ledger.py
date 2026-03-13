"""Tests for LedgerService — reward recording, penalty, and balance."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentrelay.services.ledger_service import LedgerService


def _make_ledger_entry(agent_id=None, task_id=None, amount=0.0, entry_type="reward"):
    entry = MagicMock()
    entry.id = uuid.uuid4()
    entry.agent_id = agent_id or uuid.uuid4()
    entry.task_id = task_id or uuid.uuid4()
    entry.amount = amount
    entry.entry_type = entry_type
    entry.created_at = datetime.now(timezone.utc)
    entry.updated_at = datetime.now(timezone.utc)
    return entry


class TestLedgerService:
    def _build(self):
        repo = AsyncMock()
        svc = LedgerService(repo)
        return svc, repo

    @pytest.mark.asyncio
    async def test_record_reward(self):
        svc, repo = self._build()
        agent_id = uuid.uuid4()
        task_id = uuid.uuid4()
        amount = 5.0
        repo.create.return_value = _make_ledger_entry(
            agent_id=agent_id, task_id=task_id, amount=amount, entry_type="reward"
        )

        result = await svc.record_reward(agent_id, task_id, amount)

        repo.create.assert_called_once_with(
            agent_id=agent_id,
            task_id=task_id,
            amount=5.0,
            entry_type="reward",
        )
        assert result.amount == 5.0
        assert result.entry_type == "reward"

    @pytest.mark.asyncio
    async def test_record_penalty_stores_negative_amount(self):
        svc, repo = self._build()
        agent_id = uuid.uuid4()
        task_id = uuid.uuid4()
        repo.create.return_value = _make_ledger_entry(
            agent_id=agent_id, task_id=task_id, amount=-3.0, entry_type="penalty"
        )

        await svc.record_penalty(agent_id, task_id, 3.0)

        call_kwargs = repo.create.call_args.kwargs
        assert call_kwargs["amount"] == -3.0
        assert call_kwargs["entry_type"] == "penalty"

    @pytest.mark.asyncio
    async def test_record_penalty_already_negative(self):
        """Passing a negative amount should still store negative."""
        svc, repo = self._build()
        repo.create.return_value = _make_ledger_entry(amount=-2.0, entry_type="penalty")

        await svc.record_penalty(uuid.uuid4(), uuid.uuid4(), -2.0)

        call_kwargs = repo.create.call_args.kwargs
        assert call_kwargs["amount"] == -2.0

    @pytest.mark.asyncio
    async def test_get_balance(self):
        svc, repo = self._build()
        repo.get_balance.return_value = 42.5

        balance = await svc.get_balance(uuid.uuid4())

        assert balance == 42.5
        repo.get_balance.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_balance_zero(self):
        svc, repo = self._build()
        repo.get_balance.return_value = 0.0

        balance = await svc.get_balance(uuid.uuid4())

        assert balance == 0.0

    @pytest.mark.asyncio
    async def test_reward_then_penalty_balance(self):
        """Integration-style test: record reward + penalty, check balance reflects both."""
        svc, repo = self._build()
        agent_id = uuid.uuid4()

        repo.create.return_value = _make_ledger_entry(amount=10.0)
        await svc.record_reward(agent_id, uuid.uuid4(), 10.0)

        repo.create.return_value = _make_ledger_entry(amount=-3.0)
        await svc.record_penalty(agent_id, uuid.uuid4(), 3.0)

        # Simulate balance = 10 - 3 = 7
        repo.get_balance.return_value = 7.0
        balance = await svc.get_balance(agent_id)

        assert balance == 7.0
