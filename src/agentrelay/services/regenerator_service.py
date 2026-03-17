"""Task regenerator — replenish open tasks to maintain a target pool size."""

from __future__ import annotations

import logging
import secrets

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agentrelay.models.agent import Agent
from agentrelay.models.task import Task
from agentrelay.tasks.generator import generate_tasks
from agentrelay.schemas.task import TaskCreate
from agentrelay.services.task_service import TaskService
from agentrelay.repositories.task_repo import TaskRepository
from agentrelay.repositories.submission_repo import SubmissionRepository

logger = logging.getLogger(__name__)

SYSTEM_PUBLISHER_NAME = "agentrelay-system"


class TaskRegenerator:
    """Keeps the open-task pool at a target size by generating new tasks."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        target_open_tasks: int = 20,
        check_interval: int = 3600,
    ) -> None:
        self.session_factory = session_factory
        self.target_open_tasks = target_open_tasks
        self.check_interval = check_interval

    async def ensure_system_publisher(self, session: AsyncSession) -> str:
        """Return the agent_id of the system publisher, creating one if needed."""
        stmt = select(Agent).where(Agent.name == SYSTEM_PUBLISHER_NAME)
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()

        if agent is not None:
            return str(agent.id)

        new_agent = Agent(
            name=SYSTEM_PUBLISHER_NAME,
            api_key=secrets.token_hex(32),
            capabilities={"roles": ["publisher"]},
        )
        session.add(new_agent)
        await session.flush()
        return str(new_agent.id)

    async def count_open_tasks(self, session: AsyncSession) -> int:
        """Count tasks with status='open'."""
        stmt = select(func.count()).select_from(Task).where(Task.status == "open")
        result = await session.execute(stmt)
        return result.scalar_one()

    async def check_and_replenish(self) -> int:
        """Check open task count and create new tasks if below target.

        Returns the number of new tasks created.
        """
        async with self.session_factory() as session:
            current = await self.count_open_tasks(session)

            if current >= self.target_open_tasks:
                logger.info(
                    "[Regenerator] %d open tasks >= target %d, skipping",
                    current,
                    self.target_open_tasks,
                )
                return 0

            deficit = self.target_open_tasks - current
            publisher_id = await self.ensure_system_publisher(session)

            payloads = generate_tasks(publisher_id, count=deficit)

            task_svc = TaskService(
                task_repo=TaskRepository(session),
                submission_repo=SubmissionRepository(session),
            )
            items = [TaskCreate(**p) for p in payloads]
            await task_svc.create_tasks_batch(items)
            await session.commit()

            logger.info(
                "[Regenerator] Created %d new tasks (was %d, target %d)",
                deficit,
                current,
                self.target_open_tasks,
            )
            return deficit
