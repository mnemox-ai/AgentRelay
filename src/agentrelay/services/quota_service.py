"""Quota service — check agent token/task budgets."""

from __future__ import annotations

import uuid

from agentrelay.domain.quota_profile import QuotaProfile
from agentrelay.models.task import Task
from agentrelay.repositories.agent_repo import AgentRepository
from agentrelay.repositories.task_repo import TaskRepository


class QuotaExceededError(Exception):
    """Raised when an agent's quota is exceeded."""


class QuotaService:
    def __init__(
        self,
        task_repo: TaskRepository | None = None,
        agent_repo: AgentRepository | None = None,
    ) -> None:
        self.task_repo = task_repo
        self.agent_repo = agent_repo

    def check_quota(self, quota_profile: QuotaProfile, token_estimate: int) -> bool:
        if token_estimate < 0:
            return False
        if token_estimate > quota_profile.safe_token_cap:
            return False
        return True

    async def check_and_deduct_quota(
        self, agent_id: uuid.UUID, task: Task
    ) -> None:
        """Check daily budget and token cap before allowing a claim.

        Raises QuotaExceededError if any limit is breached.
        """
        if self.agent_repo is None or self.task_repo is None:
            raise RuntimeError("QuotaService requires task_repo and agent_repo")

        quota = await self.agent_repo.get_quota_profile(agent_id)
        if quota is None:
            return  # no quota configured — allow

        # Check token cap
        token_estimate = (getattr(task, "task_spec", None) or {}).get(
            "token_estimate", 0
        )
        if token_estimate > 0 and token_estimate > quota.safe_token_cap:
            raise QuotaExceededError(
                f"Token budget exceeded: task requires {token_estimate} "
                f"tokens but agent cap is {quota.safe_token_cap}"
            )

        # Check daily task budget
        if quota.daily_task_budget > 0:
            claimed_today = await self.task_repo.count_claimed_today(agent_id)
            if claimed_today >= quota.daily_task_budget:
                raise QuotaExceededError(
                    f"Daily task budget exceeded: {claimed_today}/{quota.daily_task_budget} tasks claimed today"
                )
