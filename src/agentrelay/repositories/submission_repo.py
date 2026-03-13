"""Async CRUD repository for Submission model."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.models.submission import Submission


class SubmissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs) -> Submission:
        submission = Submission(**kwargs)
        self.session.add(submission)
        await self.session.flush()
        return submission

    async def get(self, submission_id: uuid.UUID) -> Submission | None:
        return await self.session.get(Submission, submission_id)

    async def get_by_task(self, task_id: uuid.UUID) -> list[Submission]:
        stmt = select(Submission).where(Submission.task_id == task_id).order_by(Submission.submitted_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
