"""Task lifecycle service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import logging

from agentrelay.domain.capability import AgentCapability
from agentrelay.domain.task_lifecycle import TaskStateMachine
from agentrelay.domain.task_spec import TaskDifficulty, TaskStatus, TaskType
from agentrelay.models.task import Task
from agentrelay.models.submission import Submission
from agentrelay.repositories.agent_repo import AgentRepository
from agentrelay.repositories.task_repo import TaskRepository
from agentrelay.repositories.submission_repo import SubmissionRepository
from agentrelay.schemas.task import TaskCreate
from agentrelay.schemas.submission import SubmissionCreate

logger = logging.getLogger(__name__)

if __import__("typing").TYPE_CHECKING:
    from agentrelay.services.ledger_service import LedgerService
    from agentrelay.services.quota_service import QuotaService
    from agentrelay.services.reputation_service import ReputationService
    from agentrelay.services.validation_service import ValidationService


class TaskService:
    def __init__(
        self,
        task_repo: TaskRepository,
        submission_repo: SubmissionRepository,
        agent_repo: AgentRepository | None = None,
        validation_svc: ValidationService | None = None,
        ledger_svc: LedgerService | None = None,
        reputation_svc: ReputationService | None = None,
        quota_svc: QuotaService | None = None,
    ) -> None:
        self.task_repo = task_repo
        self.submission_repo = submission_repo
        self.agent_repo = agent_repo
        self.validation_svc = validation_svc
        self.ledger_svc = ledger_svc
        self.reputation_svc = reputation_svc
        self.quota_svc = quota_svc

    async def create_task(self, data: TaskCreate) -> Task:
        deadline_at = None
        if data.deadline_seconds is not None:
            deadline_at = datetime.now(timezone.utc) + timedelta(seconds=data.deadline_seconds)

        return await self.task_repo.create(
            task_spec=data.task_spec,
            publisher_id=data.publisher_id,
            reward=data.reward,
            deadline_at=deadline_at,
        )

    async def create_tasks_batch(self, items: list[TaskCreate]) -> list[Task]:
        return await self.task_repo.create_batch([
            dict(
                task_spec=data.task_spec,
                publisher_id=data.publisher_id,
                reward=data.reward,
                deadline_at=(
                    datetime.now(timezone.utc) + timedelta(seconds=data.deadline_seconds)
                    if data.deadline_seconds is not None else None
                ),
            )
            for data in items
        ])

    async def claim_task(self, task_id: uuid.UUID, agent_id: uuid.UUID) -> Task | None:
        # Double-check with row-level lock to prevent concurrent claims
        task = await self.task_repo.get_for_update(task_id)
        if task is None:
            raise ValueError("Task not found")
        TaskStateMachine.transition(task.status, "claimed")
        now = datetime.now(timezone.utc)
        return await self.task_repo.update_status(task_id, "claimed", claimed_by=agent_id, claimed_at=now)

    async def get_task(self, task_id: uuid.UUID) -> Task | None:
        return await self.task_repo.get(task_id)

    async def get_open_tasks_by_ids(self, task_ids: list[uuid.UUID]) -> list[Task]:
        """Fetch tasks by IDs, returning only those with open status."""
        return await self.task_repo.list_open_by_ids(task_ids)

    async def get_available_tasks(self, limit: int = 50) -> list[Task]:
        return await self.task_repo.list_available(limit=limit)

    async def update_task_status(self, task_id: uuid.UUID, status: str) -> Task | None:
        return await self.task_repo.update_status(task_id, status)

    async def claim_task_with_quota(self, task_id: uuid.UUID, agent_id: uuid.UUID) -> Task:
        """Check quota then claim. Raises QuotaExceededError or ValueError."""
        task = await self.task_repo.get(task_id)
        if task is not None and self.quota_svc is not None:
            await self.quota_svc.check_and_deduct_quota(agent_id, task)
        return await self.claim_task(task_id, agent_id)

    async def submit_and_process(self, data: SubmissionCreate) -> tuple[Submission, str]:
        """Submit, validate, update status, record ledger and reputation.

        Returns (submission, final_status).
        """
        submission = await self.submit_task(data)

        task = await self.task_repo.get(data.task_id)
        await self.task_repo.update_status(data.task_id, TaskStatus.VALIDATING.value)

        result = await self.validation_svc.validate_submission(submission, task)

        final_status = TaskStatus.COMPLETED.value if result.passed else TaskStatus.FAILED.value
        await self.task_repo.update_status(data.task_id, final_status)

        if self.ledger_svc is not None:
            if result.passed:
                await self.ledger_svc.record_reward(data.agent_id, data.task_id, task.reward)
            else:
                await self.ledger_svc.record_penalty(data.agent_id, data.task_id, task.reward)

        if self.reputation_svc is not None:
            await self.reputation_svc.update_reputation(data.agent_id, result)

        return submission, final_status

    async def submit_task(self, data: SubmissionCreate) -> Submission:
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

    async def match_tasks_for_agent(self, agent_id: uuid.UUID) -> list[Task]:
        """Return available tasks filtered by agent's capabilities and quota."""
        if self.agent_repo is None:
            raise ValueError("AgentRepository required for capability matching")

        agent = await self.agent_repo.get(agent_id)
        if agent is None:
            raise ValueError("Agent not found")

        capability = AgentCapability.from_dict(agent.capabilities or {})
        quota = await self.agent_repo.get_quota_profile(agent_id)
        safe_token_cap = quota.safe_token_cap if quota else 0

        all_tasks = await self.task_repo.list_available()
        matched: list[Task] = []

        for task in all_tasks:
            spec = task.task_spec or {}

            # Filter by task_type
            raw_type = spec.get("task_type") or spec.get("type")
            if raw_type:
                try:
                    task_type = TaskType(raw_type)
                    if not capability.supports_task_type(task_type):
                        continue
                except ValueError:
                    logger.warning("Unknown task_type value: %s", raw_type)

            # Filter by difficulty
            raw_diff = spec.get("difficulty")
            if raw_diff:
                try:
                    difficulty = TaskDifficulty(raw_diff)
                    if not capability.supports_difficulty(difficulty):
                        continue
                except ValueError:
                    logger.warning("Unknown difficulty value: %s", raw_diff)

            # Filter by token_estimate vs safe_token_cap
            token_estimate = spec.get("token_estimate", 0)
            if token_estimate > 0 and safe_token_cap > 0:
                if token_estimate > safe_token_cap:
                    continue

            matched.append(task)

        return matched
