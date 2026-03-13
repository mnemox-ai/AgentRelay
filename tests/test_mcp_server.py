"""Tests for MCP Server tools."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agentrelay.models.base import Base
from agentrelay.models.agent import Agent
from agentrelay.models.task import Task
from agentrelay.security.auth import generate_api_key

# ---------------------------------------------------------------------------
# Test DB (independent engine so MCP tools use the same in-memory DB)
# ---------------------------------------------------------------------------

_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
_SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _mcp_db():
    """Create/drop tables on the MCP-test engine."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def _patch_session_factory(monkeypatch):
    """Point MCP server at the test DB."""
    monkeypatch.setattr(
        "agentrelay.mcp_server._get_session_factory", lambda: _SessionFactory
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_agent(name: str = "test-agent") -> tuple[Agent, str]:
    """Insert an agent and return (agent, api_key)."""
    api_key = generate_api_key()
    async with _SessionFactory() as session:
        agent = Agent(name=name, api_key=api_key, quota_profile={}, capabilities={})
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
    return agent, api_key


async def _create_task_row(publisher_id: uuid.UUID, **overrides) -> Task:
    """Insert a task directly."""
    defaults = {
        "task_spec": {"task_type": "coding", "output_schema": {}, "validation_method": "schema"},
        "status": "open",
        "publisher_id": publisher_id,
        "reward": 1.0,
    }
    defaults.update(overrides)
    async with _SessionFactory() as session:
        task = Task(**defaults)
        session.add(task)
        await session.commit()
        await session.refresh(task)
    return task


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAuthentication:
    async def test_invalid_api_key_raises(self):
        from agentrelay.mcp_server import list_tasks

        with pytest.raises(ValueError, match="Invalid API key"):
            await list_tasks(api_key="bad-key-000000")


class TestListTasks:
    async def test_empty(self):
        from agentrelay.mcp_server import list_tasks

        agent, key = await _create_agent()
        result = await list_tasks(api_key=key)
        assert result == []

    async def test_returns_open_tasks(self):
        from agentrelay.mcp_server import list_tasks

        agent, key = await _create_agent()
        await _create_task_row(agent.id)
        await _create_task_row(agent.id, reward=5.0)

        result = await list_tasks(api_key=key)
        assert len(result) == 2
        assert all(t["status"] == "open" for t in result)


class TestGetTask:
    async def test_found(self):
        from agentrelay.mcp_server import get_task

        agent, key = await _create_agent()
        task = await _create_task_row(agent.id, reward=3.0)

        result = await get_task(api_key=key, task_id=str(task.id))
        assert result["id"] == str(task.id)
        assert result["reward"] == 3.0

    async def test_not_found(self):
        from agentrelay.mcp_server import get_task

        agent, key = await _create_agent()
        with pytest.raises(ValueError, match="not found"):
            await get_task(api_key=key, task_id=str(uuid.uuid4()))


class TestCreateTask:
    async def test_creates_task(self):
        from agentrelay.mcp_server import create_task

        agent, key = await _create_agent()
        spec = {"task_type": "coding", "output_schema": {}, "validation_method": "schema"}
        result = await create_task(api_key=key, task_spec=spec, reward=2.5)

        assert result["status"] == "open"
        assert result["reward"] == 2.5
        assert result["publisher_id"] == str(agent.id)
        assert result["id"]  # UUID string

    async def test_with_deadline(self):
        from agentrelay.mcp_server import create_task

        agent, key = await _create_agent()
        result = await create_task(
            api_key=key,
            task_spec={"task_type": "coding", "output_schema": {}, "validation_method": "schema"},
            deadline_seconds=3600,
        )
        assert result["deadline_at"] is not None


class TestClaimTask:
    async def test_claim_open_task(self):
        from agentrelay.mcp_server import claim_task

        publisher, pub_key = await _create_agent("publisher")
        claimer, claim_key = await _create_agent("claimer")
        task = await _create_task_row(publisher.id)

        result = await claim_task(api_key=claim_key, task_id=str(task.id))
        assert result["status"] == "claimed"
        assert result["claimed_by"] == str(claimer.id)

    async def test_claim_already_claimed_fails(self):
        from agentrelay.mcp_server import claim_task

        publisher, pub_key = await _create_agent("pub2")
        claimer1, key1 = await _create_agent("claimer1")
        claimer2, key2 = await _create_agent("claimer2")
        task = await _create_task_row(publisher.id)

        await claim_task(api_key=key1, task_id=str(task.id))
        with pytest.raises(Exception):
            await claim_task(api_key=key2, task_id=str(task.id))


class TestSubmitTask:
    async def test_submit_claimed_task(self):
        from agentrelay.mcp_server import claim_task, submit_task

        publisher, pub_key = await _create_agent("sub-pub")
        worker, worker_key = await _create_agent("sub-worker")
        task = await _create_task_row(publisher.id)

        await claim_task(api_key=worker_key, task_id=str(task.id))

        result = await submit_task(
            api_key=worker_key,
            task_id=str(task.id),
            output_data={"answer": 42},
        )
        assert result["task_id"] == str(task.id)
        assert result["agent_id"] == str(worker.id)
        assert result["output_data"] == {"answer": 42}

    async def test_submit_unclaimed_fails(self):
        from agentrelay.mcp_server import submit_task

        publisher, pub_key = await _create_agent("sub-pub2")
        worker, worker_key = await _create_agent("sub-worker2")
        task = await _create_task_row(publisher.id)

        with pytest.raises(Exception):
            await submit_task(
                api_key=worker_key,
                task_id=str(task.id),
                output_data={"answer": 0},
            )


class TestGetAgentReputation:
    async def test_no_reputation_yet(self):
        from agentrelay.mcp_server import get_agent_reputation

        agent, key = await _create_agent("rep-agent")
        result = await get_agent_reputation(api_key=key, agent_id=str(agent.id))
        assert result["metrics"] is None
        assert "No reputation" in result["message"]
