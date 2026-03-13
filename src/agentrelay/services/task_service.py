"""Task lifecycle service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from agentrelay.domain.task_lifecycle import TaskStateMachine
from agentrelay.repositories.task_repo import TaskRepository
from agentrelay.repositories.submission_repo import SubmissionRepository
from agentrelay.schemas.task import TaskCreate
from agentrelay.schemas.submission import SubmissionCreate


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        submission_repo: SubmissionRepository,
    ) -> None:
        self.task_repo = task_repo
        self.submission_repo = submission_repo

    async def create_task(self, data: TaskCreate):
        deadline_at = None
        if data.deadline_seconds is not None:
            deadline_at = datetime.now(timezone.utc) + timedelta(seconds=data.deadline_seconds)

        return await self.task_repo.create(
            task_spec=data.task_spec,
            publisher_id=data.publisher_id,
            reward=data.reward,
            deadline_at=deadline_at,
        )

    async def claim_task(self, task_id: uuid.UUID, agent_id: uuid.UUID):
        # Double-check with row-level lock to prevent concurrent claims
        task = await self.task_repo.get_for_update(task_id)
        if task is None:
            raise ValueError("Task not found")
        TaskStateMachine.transition(task.status, "claimed")
        now = datetime.now(timezone.utc)
        return await self.task_repo.update_status(task_id, "claimed", claimed_by=agent_id, claimed_at=now)

    async def get_available_tasks(self, limit: int = 50):
        return await self.task_repo.list_available(limit=limit)

    async def submit_task(self, data: SubmissionCreate):
        task = await self.task_repo.get(data.task_id)
        if task is None:
            raise ValueError("Task not found")
        TaskStateMachine.transition(task.status, "submitted")
        if task.claimed_by != data.agent_id:
            raise ValueError("Agent did not claim this task")

        submission = await self.submission_repo.create(
            task_id=data.task_id,
            agent_id=data.agent_id,
            output_data=data.output_data,
        )
        now = datetime.now(timezone.utc)
        await self.task_repo.update_status(data.task_id, "submitted", submitted_at=now)
        return submission
