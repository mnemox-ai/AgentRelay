"""End-to-end MCP integration tests — full task lifecycle via MCP tools.

Simulates a complete MCP flow:
  1. discover_capabilities → query system capabilities
  2. create_task → publish a task
  3. list_tasks → verify task is visible
  4. claim_task → worker claims it
  5. submit_task → worker submits output
  6. Validation pipeline → task becomes COMPLETED
  7. get_agent_reputation → reputation updated
"""

from __future__ import annotations

import uuid

from agentrelay.domain.task_lifecycle import InvalidTransitionError

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from agentrelay.models.base import Base
from agentrelay.models.agent import Agent
from agentrelay.security.auth import generate_api_key

# ---------------------------------------------------------------------------
# Test DB (independent engine — MCP tools share this in-memory DB)
# ---------------------------------------------------------------------------

_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
_SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _mcp_db():
    """Create/drop tables for each test."""
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

async def _register_agent(name: str) -> tuple[Agent, str]:
    """Insert an agent and return (agent, api_key)."""
    api_key = generate_api_key()
    async with _SessionFactory() as session:
        agent = Agent(name=name, api_key=api_key, quota_profile={}, capabilities={})
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
    return agent, api_key


# Shared task spec with a JSON Schema that validates our expected output
TASK_SPEC = {
    "task_type": "data_structuring",
    "difficulty": "easy",
    "input_data": {"raw_text": "Extract the capital of France."},
    "output_schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
        },
        "required": ["answer"],
    },
    "validation_method": "schema+rule",
    "token_estimate": 100,
}

VALID_OUTPUT = {"answer": "Paris"}
INVALID_OUTPUT = {"answer": 42}  # wrong type — schema validation will fail


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMcpEndToEndHappyPath:
    """Full lifecycle: discover → create → list → claim → submit → validate → reputation."""

    async def test_complete_flow(self):
        from agentrelay.mcp_server import (
            claim_task,
            create_task,
            discover_capabilities,
            get_agent_reputation,
            get_task,
            list_tasks,
            submit_task,
        )

        # --- 0. Register publisher + worker ---
        publisher, pub_key = await _register_agent("publisher")
        worker, worker_key = await _register_agent("worker")

        # --- 1. discover_capabilities (no auth) ---
        caps = await discover_capabilities()
        assert caps["status"] == "running"
        assert "data_structuring" in caps["task_types"]
        assert "easy" in caps["difficulties"]
        assert caps["open_tasks"]["total"] == 0

        # --- 2. create_task ---
        created = await create_task(
            api_key=pub_key,
            task_spec=TASK_SPEC,
            reward=5.0,
            deadline_seconds=3600,
        )
        task_id = created["id"]
        assert created["status"] == "open"
        assert created["reward"] == 5.0
        assert created["publisher_id"] == str(publisher.id)
        assert created["deadline_at"] is not None

        # --- 3. list_tasks — task should be visible ---
        tasks = await list_tasks(api_key=worker_key)
        assert len(tasks) == 1
        assert tasks[0]["id"] == task_id
        assert tasks[0]["status"] == "open"

        # --- verify discover_capabilities reflects open task ---
        caps2 = await discover_capabilities()
        assert caps2["open_tasks"]["total"] == 1

        # --- 4. claim_task ---
        claimed = await claim_task(api_key=worker_key, task_id=task_id)
        assert claimed["status"] == "claimed"
        assert claimed["claimed_by"] == str(worker.id)

        # --- verify task no longer in available list ---
        tasks_after_claim = await list_tasks(api_key=worker_key)
        assert len(tasks_after_claim) == 0

        # --- 5. submit_task ---
        submission = await submit_task(
            api_key=worker_key,
            task_id=task_id,
            output_data=VALID_OUTPUT,
        )
        assert submission["task_id"] == task_id
        assert submission["agent_id"] == str(worker.id)
        assert submission["output_data"] == VALID_OUTPUT

        # --- verify task status is "submitted" ---
        task_after_submit = await get_task(api_key=pub_key, task_id=task_id)
        assert task_after_submit["status"] == "submitted"

        # --- 6. Run validation pipeline (simulates what REST route does) ---
        from agentrelay.repositories.task_repo import TaskRepository
        from agentrelay.repositories.submission_repo import SubmissionRepository
        from agentrelay.repositories.reputation_repo import ReputationRepository
        from agentrelay.repositories.ledger_repo import LedgerRepository
        from agentrelay.services.validation_service import ValidationService
        from agentrelay.services.reputation_service import ReputationService
        from agentrelay.services.ledger_service import LedgerService

        async with _SessionFactory() as session:
            task_repo = TaskRepository(session)
            sub_repo = SubmissionRepository(session)

            task_obj = await task_repo.get(uuid.UUID(task_id))
            subs = await sub_repo.get_by_task(uuid.UUID(task_id))
            assert len(subs) == 1
            sub_obj = subs[0]

            # Transition: submitted → validating
            await task_repo.update_status(uuid.UUID(task_id), "validating")

            validation_svc = ValidationService(session=session)
            result = await validation_svc.validate_submission(sub_obj, task_obj)
            assert result.passed is True
            assert result.score == 1.0

            # Transition: validating → completed
            await task_repo.update_status(uuid.UUID(task_id), "completed")

            # Record reward
            ledger_svc = LedgerService(LedgerRepository(session))
            await ledger_svc.record_reward(worker.id, uuid.UUID(task_id), 5.0)

            # Update reputation
            reputation_svc = ReputationService(ReputationRepository(session))
            await reputation_svc.update_reputation(worker.id, result)

            await session.commit()

        # --- verify final task status via MCP ---
        final_task = await get_task(api_key=pub_key, task_id=task_id)
        assert final_task["status"] == "completed"

        # --- 7. get_agent_reputation ---
        rep = await get_agent_reputation(api_key=worker_key, agent_id=str(worker.id))
        assert rep["metrics"] is not None
        assert rep["metrics"]["total_submissions"] == 1
        assert rep["metrics"]["passed"] == 1
        assert rep["metrics"]["failed"] == 0
        assert rep["metrics"]["pass_rate"] == 1.0
        assert rep["metrics"]["quality_score"] == 100.0


class TestMcpEndToEndFailedValidation:
    """Submit invalid output → validation fails → task status = failed, reputation reflects failure."""

    async def test_failed_validation_flow(self):
        from agentrelay.mcp_server import (
            claim_task,
            create_task,
            get_agent_reputation,
            get_task,
            submit_task,
        )

        publisher, pub_key = await _register_agent("fail-pub")
        worker, worker_key = await _register_agent("fail-worker")

        # Create task with strict schema
        created = await create_task(api_key=pub_key, task_spec=TASK_SPEC, reward=3.0)
        task_id = created["id"]

        # Claim + submit with INVALID output
        await claim_task(api_key=worker_key, task_id=task_id)
        await submit_task(
            api_key=worker_key,
            task_id=task_id,
            output_data=INVALID_OUTPUT,
        )

        # Run validation pipeline
        from agentrelay.repositories.task_repo import TaskRepository
        from agentrelay.repositories.submission_repo import SubmissionRepository
        from agentrelay.repositories.reputation_repo import ReputationRepository
        from agentrelay.repositories.ledger_repo import LedgerRepository
        from agentrelay.services.validation_service import ValidationService
        from agentrelay.services.reputation_service import ReputationService
        from agentrelay.services.ledger_service import LedgerService

        async with _SessionFactory() as session:
            task_repo = TaskRepository(session)
            sub_repo = SubmissionRepository(session)

            task_obj = await task_repo.get(uuid.UUID(task_id))
            subs = await sub_repo.get_by_task(uuid.UUID(task_id))
            sub_obj = subs[0]

            await task_repo.update_status(uuid.UUID(task_id), "validating")

            validation_svc = ValidationService(session=session)
            result = await validation_svc.validate_submission(sub_obj, task_obj)
            assert result.passed is False

            # Transition: validating → failed
            await task_repo.update_status(uuid.UUID(task_id), "failed")

            # Record penalty
            ledger_svc = LedgerService(LedgerRepository(session))
            await ledger_svc.record_penalty(worker.id, uuid.UUID(task_id), 3.0)

            # Update reputation
            reputation_svc = ReputationService(ReputationRepository(session))
            await reputation_svc.update_reputation(worker.id, result)

            await session.commit()

        # Verify task failed
        final_task = await get_task(api_key=pub_key, task_id=task_id)
        assert final_task["status"] == "failed"

        # Verify reputation reflects failure
        rep = await get_agent_reputation(api_key=worker_key, agent_id=str(worker.id))
        assert rep["metrics"]["total_submissions"] == 1
        assert rep["metrics"]["passed"] == 0
        assert rep["metrics"]["failed"] == 1
        assert rep["metrics"]["pass_rate"] == 0.0


class TestMcpEndToEndMultipleTasks:
    """Worker completes multiple tasks — reputation accumulates correctly."""

    async def test_two_tasks_reputation_accumulates(self):
        from agentrelay.mcp_server import (
            claim_task,
            create_task,
            get_agent_reputation,
            list_tasks,
            submit_task,
        )

        publisher, pub_key = await _register_agent("multi-pub")
        worker, worker_key = await _register_agent("multi-worker")

        from agentrelay.repositories.task_repo import TaskRepository
        from agentrelay.repositories.submission_repo import SubmissionRepository
        from agentrelay.repositories.reputation_repo import ReputationRepository
        from agentrelay.services.validation_service import ValidationService
        from agentrelay.services.reputation_service import ReputationService

        # Create, claim, and submit two tasks via MCP
        task_ids = []
        for _ in range(2):
            created = await create_task(api_key=pub_key, task_spec=TASK_SPEC, reward=1.0)
            tid = created["id"]
            task_ids.append(tid)
            await claim_task(api_key=worker_key, task_id=tid)
            await submit_task(
                api_key=worker_key,
                task_id=tid,
                output_data=VALID_OUTPUT,
            )

        # Run validation for both tasks in a single session to ensure
        # reputation accumulates correctly across submissions
        async with _SessionFactory() as session:
            task_repo = TaskRepository(session)
            sub_repo = SubmissionRepository(session)
            reputation_svc = ReputationService(ReputationRepository(session))

            for tid in task_ids:
                task_obj = await task_repo.get(uuid.UUID(tid))
                subs = await sub_repo.get_by_task(uuid.UUID(tid))
                sub_obj = subs[0]
                await task_repo.update_status(uuid.UUID(tid), "validating")

                validation_svc = ValidationService(session=session)
                result = await validation_svc.validate_submission(sub_obj, task_obj)
                assert result.passed is True

                await task_repo.update_status(uuid.UUID(tid), "completed")
                await reputation_svc.update_reputation(worker.id, result)

            await session.commit()

        # Verify accumulated reputation
        rep = await get_agent_reputation(api_key=worker_key, agent_id=str(worker.id))
        assert rep["metrics"]["total_submissions"] == 2
        assert rep["metrics"]["passed"] == 2
        assert rep["metrics"]["pass_rate"] == 1.0
        assert rep["metrics"]["quality_score"] == 100.0

        # Verify no open tasks remaining
        tasks = await list_tasks(api_key=worker_key)
        assert len(tasks) == 0


class TestMcpEdgeCases:
    """Edge cases: double claim, submit without claim, discover without DB data."""

    async def test_double_claim_rejected(self):
        from agentrelay.mcp_server import claim_task, create_task

        publisher, pub_key = await _register_agent("edge-pub")
        worker1, key1 = await _register_agent("edge-w1")
        worker2, key2 = await _register_agent("edge-w2")

        created = await create_task(api_key=pub_key, task_spec=TASK_SPEC, reward=1.0)
        task_id = created["id"]

        await claim_task(api_key=key1, task_id=task_id)
        with pytest.raises(InvalidTransitionError):
            await claim_task(api_key=key2, task_id=task_id)

    async def test_submit_unclaimed_rejected(self):
        from agentrelay.mcp_server import create_task, submit_task

        publisher, pub_key = await _register_agent("edge-pub2")
        worker, worker_key = await _register_agent("edge-w3")

        created = await create_task(api_key=pub_key, task_spec=TASK_SPEC, reward=1.0)
        task_id = created["id"]

        with pytest.raises(InvalidTransitionError):
            await submit_task(
                api_key=worker_key,
                task_id=task_id,
                output_data=VALID_OUTPUT,
            )

    async def test_discover_capabilities_shows_task_types(self):
        from agentrelay.mcp_server import create_task, discover_capabilities

        publisher, pub_key = await _register_agent("edge-pub3")

        # Create tasks of different types
        spec_coding = dict(TASK_SPEC, task_type="coding")
        spec_research = dict(TASK_SPEC, task_type="research_extraction")
        await create_task(api_key=pub_key, task_spec=spec_coding, reward=1.0)
        await create_task(api_key=pub_key, task_spec=spec_research, reward=1.0)

        caps = await discover_capabilities()
        assert caps["open_tasks"]["total"] == 2
        assert caps["open_tasks"]["by_type"]["coding"] == 1
        assert caps["open_tasks"]["by_type"]["research_extraction"] == 1
