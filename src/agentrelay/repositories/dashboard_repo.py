"""Async read-only repository for dashboard aggregate queries."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.models.agent import Agent
from agentrelay.models.ledger import LedgerEntry
from agentrelay.models.reputation import ReputationSnapshot
from agentrelay.models.submission import Submission
from agentrelay.models.task import Task
from agentrelay.models.validation_run import ValidationRun


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_stats(self) -> dict:
        total_tasks = (await self.session.execute(select(func.count(Task.id)))).scalar_one()
        completed_tasks = (
            await self.session.execute(select(func.count(Task.id)).where(Task.status == "completed"))
        ).scalar_one()
        active_agents = (
            await self.session.execute(select(func.count(Agent.id)).where(Agent.status == "active"))
        ).scalar_one()
        total_rewards = (
            await self.session.execute(
                select(func.coalesce(func.sum(LedgerEntry.amount), 0.0)).where(
                    LedgerEntry.entry_type == "reward"
                )
            )
        ).scalar_one()
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "active_agents": active_agents,
            "total_rewards": float(total_rewards),
        }

    async def get_recent_tasks(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(Task, Agent.name.label("agent_name"))
            .outerjoin(Agent, Task.claimed_by == Agent.id)
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        tasks = []
        for row in rows:
            task = row[0]
            agent_name = row[1]

            score_stmt = (
                select(func.max(ValidationRun.score))
                .join(Submission, ValidationRun.submission_id == Submission.id)
                .where(Submission.task_id == task.id)
            )
            score_result = await self.session.execute(score_stmt)
            validation_score = score_result.scalar_one_or_none()

            tasks.append({
                "id": task.id,
                "task_spec": task.task_spec,
                "status": task.status,
                "reward": task.reward,
                "created_at": task.created_at,
                "agent_name": agent_name,
                "validation_score": float(validation_score) if validation_score is not None else None,
            })

        return tasks

    async def get_top_agents(self, limit: int = 5) -> list[dict]:
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
            .order_by(ReputationSnapshot.snapshot_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        agents = []
        for row in rows:
            snapshot = row[0]
            name = row[1]
            metrics = snapshot.metrics or {}
            agents.append({
                "id": snapshot.agent_id,
                "name": name,
                "quality_score": metrics.get("quality_score", 0.0),
                "total_submissions": metrics.get("total_submissions", 0),
                "pass_rate": metrics.get("pass_rate", 0.0),
            })

        agents.sort(key=lambda a: a["quality_score"], reverse=True)
        return agents[:limit]

    async def get_validation_rate(self) -> dict:
        total = (await self.session.execute(select(func.count(ValidationRun.id)))).scalar_one()
        passed = (
            await self.session.execute(
                select(func.count(ValidationRun.id)).where(ValidationRun.passed == True)  # noqa: E712
            )
        ).scalar_one()
        rate = (passed / total * 100) if total > 0 else 0.0
        return {"passed": passed, "total": total, "rate": round(rate, 2)}

    async def get_agent_ledger(self, agent_id: uuid.UUID) -> list:
        agent = await self.session.get(Agent, agent_id)
        if agent is None:
            return None  # signal not-found to service layer
        stmt = (
            select(LedgerEntry)
            .where(LedgerEntry.agent_id == agent_id)
            .order_by(LedgerEntry.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_agent_reputation(self, agent_id: uuid.UUID) -> ReputationSnapshot | None:
        agent = await self.session.get(Agent, agent_id)
        if agent is None:
            return "agent_not_found"  # sentinel to distinguish from no-reputation
        stmt = (
            select(ReputationSnapshot)
            .where(ReputationSnapshot.agent_id == agent_id)
            .order_by(ReputationSnapshot.snapshot_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
