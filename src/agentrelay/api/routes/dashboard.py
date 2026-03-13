"""Dashboard API routes — aggregated stats for the frontend."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.api.deps import get_db, rate_limit_by_ip
from agentrelay.models.agent import Agent
from agentrelay.models.ledger import LedgerEntry
from agentrelay.models.reputation import ReputationSnapshot
from agentrelay.models.task import Task
from agentrelay.models.validation_run import ValidationRun
from agentrelay.schemas.dashboard import (
    DashboardStats,
    LedgerEntryResponse,
    RecentTask,
    TopAgent,
    ValidationRate,
)
from agentrelay.schemas.reputation import ReputationResponse

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats, dependencies=[Depends(rate_limit_by_ip)])
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Aggregated dashboard statistics."""
    total_tasks = (await db.execute(select(func.count(Task.id)))).scalar_one()
    completed_tasks = (
        await db.execute(select(func.count(Task.id)).where(Task.status == "completed"))
    ).scalar_one()
    active_agents = (
        await db.execute(select(func.count(Agent.id)).where(Agent.status == "active"))
    ).scalar_one()
    total_rewards = (
        await db.execute(
            select(func.coalesce(func.sum(LedgerEntry.amount), 0.0)).where(
                LedgerEntry.entry_type == "reward"
            )
        )
    ).scalar_one()

    return DashboardStats(
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        active_agents=active_agents,
        total_rewards=float(total_rewards),
    )


@router.get("/tasks/recent", response_model=list[RecentTask], dependencies=[Depends(rate_limit_by_ip)])
async def get_recent_tasks(db: AsyncSession = Depends(get_db)):
    """Latest 10 tasks with agent name and validation score."""
    # Get tasks with publisher name via outerjoin
    stmt = (
        select(Task, Agent.name.label("agent_name"))
        .outerjoin(Agent, Task.claimed_by == Agent.id)
        .order_by(Task.created_at.desc())
        .limit(10)
    )
    result = await db.execute(stmt)
    rows = result.all()

    tasks = []
    for row in rows:
        task = row[0]
        agent_name = row[1]

        # Get best validation score for this task's submissions
        score_stmt = (
            select(func.max(ValidationRun.score))
            .join(
                Task,
                ValidationRun.submission_id.in_(
                    select(func.distinct(ValidationRun.submission_id))
                ),
            )
        )
        # Simpler approach: query via submission
        from agentrelay.models.submission import Submission

        score_stmt = (
            select(func.max(ValidationRun.score))
            .join(Submission, ValidationRun.submission_id == Submission.id)
            .where(Submission.task_id == task.id)
        )
        score_result = await db.execute(score_stmt)
        validation_score = score_result.scalar_one_or_none()

        tasks.append(
            RecentTask(
                id=task.id,
                task_spec=task.task_spec,
                status=task.status,
                reward=task.reward,
                created_at=task.created_at,
                agent_name=agent_name,
                validation_score=float(validation_score) if validation_score is not None else None,
            )
        )

    return tasks


@router.get("/agents/top", response_model=list[TopAgent], dependencies=[Depends(rate_limit_by_ip)])
async def get_top_agents(db: AsyncSession = Depends(get_db)):
    """Top 5 agents by quality_score from their latest reputation snapshot."""
    # Subquery: latest snapshot per agent
    latest_sq = (
        select(
            ReputationSnapshot.agent_id,
            func.max(ReputationSnapshot.snapshot_at).label("max_snapshot"),
        )
        .group_by(ReputationSnapshot.agent_id)
        .subquery()
    )

    stmt = (
        select(ReputationSnapshot, Agent.name)
        .join(
            latest_sq,
            (ReputationSnapshot.agent_id == latest_sq.c.agent_id)
            & (ReputationSnapshot.snapshot_at == latest_sq.c.max_snapshot),
        )
        .join(Agent, ReputationSnapshot.agent_id == Agent.id)
        .order_by(
            # Sort by quality_score descending — use JSON extraction
            # SQLite and PostgreSQL both support this via the metrics JSONB field
            ReputationSnapshot.snapshot_at.desc()
        )
        .limit(5)
    )
    result = await db.execute(stmt)
    rows = result.all()

    agents = []
    for row in rows:
        snapshot = row[0]
        name = row[1]
        metrics = snapshot.metrics or {}
        agents.append(
            TopAgent(
                id=snapshot.agent_id,
                name=name,
                quality_score=metrics.get("quality_score", 0.0),
                total_submissions=metrics.get("total_submissions", 0),
                pass_rate=metrics.get("pass_rate", 0.0),
            )
        )

    # Sort by quality_score in Python (portable across SQLite/PostgreSQL)
    agents.sort(key=lambda a: a.quality_score, reverse=True)
    return agents[:5]


@router.get("/validation-rate", response_model=ValidationRate, dependencies=[Depends(rate_limit_by_ip)])
async def get_validation_rate(db: AsyncSession = Depends(get_db)):
    """Overall validation pass rate."""
    total = (await db.execute(select(func.count(ValidationRun.id)))).scalar_one()
    passed = (
        await db.execute(
            select(func.count(ValidationRun.id)).where(ValidationRun.passed == True)  # noqa: E712
        )
    ).scalar_one()

    rate = (passed / total * 100) if total > 0 else 0.0
    return ValidationRate(passed=passed, total=total, rate=round(rate, 2))


# ---------------------------------------------------------------------------
# Agent-scoped endpoints (mounted under /dashboard for grouping)
# ---------------------------------------------------------------------------


@router.get(
    "/agents/{agent_id}/ledger",
    response_model=list[LedgerEntryResponse],
    dependencies=[Depends(rate_limit_by_ip)],
)
async def get_agent_ledger(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """All ledger entries for a specific agent."""
    # Verify agent exists
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    stmt = (
        select(LedgerEntry)
        .where(LedgerEntry.agent_id == agent_id)
        .order_by(LedgerEntry.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get(
    "/agents/{agent_id}/reputation",
    response_model=ReputationResponse,
    dependencies=[Depends(rate_limit_by_ip)],
)
async def get_agent_reputation(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Latest reputation snapshot for a specific agent."""
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    stmt = (
        select(ReputationSnapshot)
        .where(ReputationSnapshot.agent_id == agent_id)
        .order_by(ReputationSnapshot.snapshot_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    snapshot = result.scalar_one_or_none()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No reputation data for this agent")

    return snapshot
