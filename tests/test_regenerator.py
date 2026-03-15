"""Tests for TaskRegenerator — replenish open tasks to target pool size."""

from __future__ import annotations

import secrets
import uuid

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from agentrelay.models.agent import Agent
from agentrelay.models.base import Base
from agentrelay.models.task import Task
from agentrelay.services.regenerator_service import TaskRegenerator, SYSTEM_PUBLISHER_NAME

# Use the same engine/session factory as conftest (shared StaticPool)
# We recreate it here because conftest is not directly importable.
_engine = create_async_engine("sqlite+aiosqlite://", echo=False, poolclass=StaticPool)
_SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _regen_db():
    """Create tables before, drop after each test."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_publisher(session: AsyncSession) -> str:
    """Create a publisher agent and return its id."""
    agent = Agent(
        name=f"test-publisher-{uuid.uuid4().hex[:8]}",
        api_key=secrets.token_hex(32),
        capabilities={"roles": ["publisher"]},
    )
    session.add(agent)
    await session.flush()
    return str(agent.id)


async def _create_open_tasks(session: AsyncSession, publisher_id: str, count: int) -> None:
    """Insert 'count' open tasks into the DB."""
    for _ in range(count):
        task = Task(
            task_spec={"task_type": "coding", "difficulty": "easy", "input_data": {}},
            publisher_id=uuid.UUID(publisher_id),
            reward=0.05,
            status="open",
        )
        session.add(task)
    await session.flush()


async def _count_open(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(Task).where(Task.status == "open")
    result = await session.execute(stmt)
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEnsureSystemPublisher:
    @pytest.mark.asyncio
    async def test_creates_new_publisher(self):
        regen = TaskRegenerator(_SessionFactory)
        async with _SessionFactory() as session:
            agent_id = await regen.ensure_system_publisher(session)
            await session.commit()

            stmt = select(Agent).where(Agent.name == SYSTEM_PUBLISHER_NAME)
            result = await session.execute(stmt)
            agent = result.scalar_one()
            assert str(agent.id) == agent_id
            assert agent.api_key  # non-empty

    @pytest.mark.asyncio
    async def test_returns_existing_publisher(self):
        regen = TaskRegenerator(_SessionFactory)
        async with _SessionFactory() as session:
            id1 = await regen.ensure_system_publisher(session)
            await session.commit()

        async with _SessionFactory() as session:
            id2 = await regen.ensure_system_publisher(session)
            assert id1 == id2


class TestCountOpenTasks:
    @pytest.mark.asyncio
    async def test_zero_when_empty(self):
        regen = TaskRegenerator(_SessionFactory)
        async with _SessionFactory() as session:
            count = await regen.count_open_tasks(session)
            assert count == 0

    @pytest.mark.asyncio
    async def test_counts_open_only(self):
        regen = TaskRegenerator(_SessionFactory)
        async with _SessionFactory() as session:
            pub_id = await _create_publisher(session)
            await _create_open_tasks(session, pub_id, 5)
            # Add a completed task — should not be counted
            task = Task(
                task_spec={"task_type": "coding"},
                publisher_id=uuid.UUID(pub_id),
                reward=0.05,
                status="completed",
            )
            session.add(task)
            await session.flush()

            count = await regen.count_open_tasks(session)
            assert count == 5


class TestCheckAndReplenish:
    @pytest.mark.asyncio
    async def test_zero_open_creates_target(self):
        """When 0 open tasks, create exactly target_open_tasks."""
        regen = TaskRegenerator(_SessionFactory, target_open_tasks=20)
        created = await regen.check_and_replenish()
        assert created == 20

        async with _SessionFactory() as session:
            count = await _count_open(session)
            assert count == 20

    @pytest.mark.asyncio
    async def test_below_target_fills_deficit(self):
        """When 15 open tasks, create exactly 5."""
        regen = TaskRegenerator(_SessionFactory, target_open_tasks=20)
        async with _SessionFactory() as session:
            pub_id = await _create_publisher(session)
            await _create_open_tasks(session, pub_id, 15)
            await session.commit()

        created = await regen.check_and_replenish()
        assert created == 5

        async with _SessionFactory() as session:
            count = await _count_open(session)
            assert count == 20

    @pytest.mark.asyncio
    async def test_at_target_creates_none(self):
        """When exactly at target, create 0."""
        regen = TaskRegenerator(_SessionFactory, target_open_tasks=10)
        async with _SessionFactory() as session:
            pub_id = await _create_publisher(session)
            await _create_open_tasks(session, pub_id, 10)
            await session.commit()

        created = await regen.check_and_replenish()
        assert created == 0

    @pytest.mark.asyncio
    async def test_above_target_creates_none(self):
        """When above target, create 0."""
        regen = TaskRegenerator(_SessionFactory, target_open_tasks=5)
        async with _SessionFactory() as session:
            pub_id = await _create_publisher(session)
            await _create_open_tasks(session, pub_id, 8)
            await session.commit()

        created = await regen.check_and_replenish()
        assert created == 0

    @pytest.mark.asyncio
    async def test_created_tasks_are_open(self):
        """All created tasks should have status='open'."""
        regen = TaskRegenerator(_SessionFactory, target_open_tasks=3)
        await regen.check_and_replenish()

        async with _SessionFactory() as session:
            stmt = select(Task)
            result = await session.execute(stmt)
            tasks = list(result.scalars().all())
            assert len(tasks) == 3
            for t in tasks:
                assert t.status == "open"

    @pytest.mark.asyncio
    async def test_created_tasks_have_valid_spec(self):
        """Created tasks should have task_spec with required fields."""
        regen = TaskRegenerator(_SessionFactory, target_open_tasks=2)
        await regen.check_and_replenish()

        async with _SessionFactory() as session:
            stmt = select(Task)
            result = await session.execute(stmt)
            tasks = list(result.scalars().all())
            for t in tasks:
                spec = t.task_spec
                assert "task_type" in spec
                assert "difficulty" in spec
                assert "input_data" in spec

    @pytest.mark.asyncio
    async def test_system_publisher_is_owner(self):
        """Created tasks should be owned by the system publisher."""
        regen = TaskRegenerator(_SessionFactory, target_open_tasks=2)
        await regen.check_and_replenish()

        async with _SessionFactory() as session:
            stmt = select(Agent).where(Agent.name == SYSTEM_PUBLISHER_NAME)
            result = await session.execute(stmt)
            publisher = result.scalar_one()

            stmt2 = select(Task)
            result2 = await session.execute(stmt2)
            tasks = list(result2.scalars().all())
            for t in tasks:
                assert t.publisher_id == publisher.id


class TestCustomConfig:
    def test_defaults(self):
        regen = TaskRegenerator(_SessionFactory)
        assert regen.target_open_tasks == 20
        assert regen.check_interval == 3600

    def test_custom_values(self):
        regen = TaskRegenerator(
            _SessionFactory,
            target_open_tasks=50,
            check_interval=600,
        )
        assert regen.target_open_tasks == 50
        assert regen.check_interval == 600
