"""Tests for QueueService (Redis sorted-set priority queue)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from agentrelay.services.queue_service import QueueService, _compute_priority, QUEUE_KEY


class TestComputePriority:
    def test_basic_priority(self):
        """reward / token_estimate * 1.0 when no deadline."""
        score = _compute_priority(reward=10.0, token_estimate=100, deadline_at=None)
        assert score == pytest.approx(0.1)

    def test_zero_token_estimate_treated_as_one(self):
        score = _compute_priority(reward=5.0, token_estimate=0, deadline_at=None)
        assert score == pytest.approx(5.0)

    def test_higher_reward_higher_priority(self):
        low = _compute_priority(reward=1.0, token_estimate=100, deadline_at=None)
        high = _compute_priority(reward=10.0, token_estimate=100, deadline_at=None)
        assert high > low

    def test_closer_deadline_higher_priority(self):
        now = datetime.now(timezone.utc)
        far = _compute_priority(reward=10.0, token_estimate=100, deadline_at=now + timedelta(hours=24))
        near = _compute_priority(reward=10.0, token_estimate=100, deadline_at=now + timedelta(hours=1))
        assert near > far

    def test_no_deadline_uses_unit_urgency(self):
        with_dl = _compute_priority(reward=10.0, token_estimate=100, deadline_at=datetime.now(timezone.utc) + timedelta(hours=1))
        without_dl = _compute_priority(reward=10.0, token_estimate=100, deadline_at=None)
        # 1 hour deadline → urgency=1.0 → same as no deadline
        assert with_dl == pytest.approx(without_dl, rel=0.1)

    def test_very_close_deadline_high_urgency(self):
        now = datetime.now(timezone.utc)
        score = _compute_priority(reward=1.0, token_estimate=100, deadline_at=now + timedelta(minutes=6))
        # 6 min = 0.1 hours → urgency = 1/0.1 = 10
        assert score == pytest.approx(0.1, rel=0.5)  # base * urgency much higher


class TestQueueService:
    @pytest.fixture
    def mock_redis(self):
        redis = AsyncMock()
        redis.zadd = AsyncMock()
        redis.zrevrange = AsyncMock(return_value=[])
        redis.zrem = AsyncMock()
        redis.zcard = AsyncMock(return_value=0)
        return redis

    @pytest.fixture
    def queue(self, mock_redis):
        return QueueService(mock_redis)

    @pytest.mark.asyncio
    async def test_enqueue(self, queue, mock_redis):
        task_id = uuid.uuid4()
        score = await queue.enqueue(task_id, reward=10.0, token_estimate=100, deadline_at=None)
        assert score == pytest.approx(0.1)
        mock_redis.zadd.assert_called_once()
        call_args = mock_redis.zadd.call_args
        assert call_args[0][0] == QUEUE_KEY
        mapping = call_args[0][1]
        assert str(task_id) in mapping

    @pytest.mark.asyncio
    async def test_enqueue_batch(self, queue, mock_redis):
        tasks = [
            {"task_id": uuid.uuid4(), "reward": 5.0, "token_estimate": 50},
            {"task_id": uuid.uuid4(), "reward": 10.0, "token_estimate": 100},
        ]
        await queue.enqueue_batch(tasks)
        mock_redis.zadd.assert_called_once()
        mapping = mock_redis.zadd.call_args[0][1]
        assert len(mapping) == 2

    @pytest.mark.asyncio
    async def test_enqueue_batch_empty(self, queue, mock_redis):
        await queue.enqueue_batch([])
        mock_redis.zadd.assert_not_called()

    @pytest.mark.asyncio
    async def test_top_n(self, queue, mock_redis):
        expected = [str(uuid.uuid4()), str(uuid.uuid4())]
        mock_redis.zrevrange.return_value = expected
        result = await queue.top_n(10)
        assert result == expected
        mock_redis.zrevrange.assert_called_once_with(QUEUE_KEY, 0, 9)

    @pytest.mark.asyncio
    async def test_remove(self, queue, mock_redis):
        task_id = uuid.uuid4()
        await queue.remove(task_id)
        mock_redis.zrem.assert_called_once_with(QUEUE_KEY, str(task_id))

    @pytest.mark.asyncio
    async def test_size(self, queue, mock_redis):
        mock_redis.zcard.return_value = 42
        result = await queue.size()
        assert result == 42

    @pytest.mark.asyncio
    async def test_priority_ordering(self, mock_redis):
        """Verify that enqueue computes correct relative scores."""
        queue = QueueService(mock_redis)

        id_low = uuid.uuid4()
        id_high = uuid.uuid4()

        score_low = await queue.enqueue(id_low, reward=1.0, token_estimate=100, deadline_at=None)
        score_high = await queue.enqueue(id_high, reward=50.0, token_estimate=100, deadline_at=None)

        assert score_high > score_low
