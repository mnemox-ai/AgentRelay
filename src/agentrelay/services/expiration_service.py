"""Expiration service — expire overdue tasks and penalise non-completing agents."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.domain.task_lifecycle import TaskStateMachine
from agentrelay.models.task import Task
from agentrelay.repositories.ledger_repo import LedgerRepository
from agentrelay.repositories.reputation_repo import ReputationRepository
from agentrelay.services.ledger_service import LedgerService

logger = logging.getLogger(__name__)

# Penalty multiplier applied to task reward for incomplete (claimed but expired) tasks
INCOMPLETE_PENALTY_MULTIPLIER = 0.5


async def expire_overdue_tasks(db: AsyncSession) -> list[dict]:
    """Find all open/claimed tasks past their deadline and transition them to expired.

    For claimed tasks, record an incomplete penalty on the agent's ledger and
    add a negative reputation snapshot.

    Returns a list of dicts describing each expired task for logging/response.
    """
    now = datetime.now(timezone.utc)

    stmt = (
        select(Task)
        .where(
            Task.status.in_(["open", "claimed"]),
            Task.deadline_at.isnot(None),
            Task.deadline_at < now,
        )
    )
    result = await db.execute(stmt)
    overdue_tasks = list(result.scalars().all())

    expired: list[dict] = []

    for task in overdue_tasks:
        # Capture original status before mutation
        previous_status = task.status
        was_claimed = previous_status == "claimed"
        claimed_agent = task.claimed_by

        # Validate transition via state machine
        TaskStateMachine.transition(previous_status, "expired")

        # Update status
        await db.execute(
            update(Task).where(Task.id == task.id).values(status="expired")
        )

        entry = {
            "task_id": str(task.id),
            "previous_status": previous_status,
            "was_claimed": was_claimed,
        }

        # Penalise agent who claimed but didn't complete
        if was_claimed and claimed_agent is not None:
            penalty_amount = task.reward * INCOMPLETE_PENALTY_MULTIPLIER
            if penalty_amount > 0:
                ledger_svc = LedgerService(LedgerRepository(db))
                await ledger_svc.record_penalty(claimed_agent, task.id, penalty_amount)

            # Record negative reputation snapshot
            rep_repo = ReputationRepository(db)
            latest = await rep_repo.get_latest(claimed_agent)
            prev = latest.metrics if latest else {
                "total_submissions": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "quality_score": 0.0,
                "rework_rate": 0.0,
                "incomplete": 0,
            }
            incomplete = prev.get("incomplete", 0) + 1
            metrics = {
                **prev,
                "incomplete": incomplete,
            }
            await rep_repo.create_snapshot(agent_id=claimed_agent, metrics=metrics)

            entry["agent_id"] = str(claimed_agent)
            entry["penalty"] = penalty_amount

        expired.append(entry)
        logger.info("Expired task %s (was %s)", task.id, previous_status)

    await db.flush()
    return expired
