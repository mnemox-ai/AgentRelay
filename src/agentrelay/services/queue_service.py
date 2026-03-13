"""Redis sorted-set priority queue for tasks."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from agentrelay.config import settings


def _compute_priority(reward: float, token_estimate: int, deadline_at: datetime | None) -> float:
    """Priority score = reward / token_estimate * urgency_factor.

    urgency_factor increases as deadline approaches.
    """
    tokens = max(token_estimate, 1)
    base = reward / tokens

    if deadline_at is not None:
        now = datetime.now(timezone.utc)
        remaining = (deadline_at - now).total_seconds() / 3600.0  # hours
        urgency = 1.0 / max(remaining, 0.1)
    else:
        urgency = 1.0

    return base * urgency


QUEUE_KEY = "agentrelay:priority_queue"


class QueueService:
    """Redis sorted-set backed priority queue."""

    def __init__(self, redis_client) -> None:
        self.redis = redis_client

    async def enqueue(self, task_id: uuid.UUID, reward: float, token_estimate: int, deadline_at: datetime | None) -> float:
        """Add task to priority queue. Returns computed score."""
        score = _compute_priority(reward, token_estimate, deadline_at)
        await self.redis.zadd(QUEUE_KEY, {str(task_id): score})
        return score

    async def enqueue_batch(self, tasks: list[dict]) -> None:
        """Enqueue multiple tasks. Each dict: {task_id, reward, token_estimate, deadline_at}."""
        if not tasks:
            return
        mapping: dict[str, float] = {}
        for t in tasks:
            score = _compute_priority(t["reward"], t["token_estimate"], t.get("deadline_at"))
            mapping[str(t["task_id"])] = score
        await self.redis.zadd(QUEUE_KEY, mapping)

    async def top_n(self, n: int = 50) -> list[str]:
        """Return top N task IDs by priority (highest first)."""
        return await self.redis.zrevrange(QUEUE_KEY, 0, n - 1)

    async def remove(self, task_id: uuid.UUID) -> None:
        """Remove task from queue (e.g. after claim)."""
        await self.redis.zrem(QUEUE_KEY, str(task_id))

    async def size(self) -> int:
        return await self.redis.zcard(QUEUE_KEY)


async def get_redis():
    """Create an async Redis client. Caller is responsible for closing."""
    import redis.asyncio as aioredis

    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)
