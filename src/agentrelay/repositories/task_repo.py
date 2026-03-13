"""Async CRUD repository for Task model."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.models.task import Task


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs) -> Task:
        task = Task(**kwargs)
        self.session.add(task)
        await self.session.flush()
        return task

    async def get(self, task_id: uuid.UUID) -> Task | None:
        return await self.session.get(Task, task_id)

    async def get_for_update(self, task_id: uuid.UUID) -> Task | None:
        """SELECT ... FOR UPDATE — acquires a row-level lock to prevent concurrent claims."""
        stmt = select(Task).where(Task.id == task_id).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_available(self, limit: int = 50) -> list[Task]:
        stmt = select(Task).where(Task.status == "open").order_by(Task.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(self, task_id: uuid.UUID, status: str, **kwargs) -> Task | None:
        stmt = update(Task).where(Task.id == task_id).values(status=status, **kwargs)
        await self.session.execute(stmt)
        await self.session.flush()
        return await self.get(task_id)
