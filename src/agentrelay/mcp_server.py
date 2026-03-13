"""MCP Server for AgentRelay — exposes task CRUD + claim + submit as MCP tools."""

from __future__ import annotations

import uuid

from fastmcp import FastMCP

mcp = FastMCP("AgentRelay")


def _get_session_factory():
    """Lazy import session factory (patchable in tests)."""
    from agentrelay.db import async_session_factory

    return async_session_factory


async def _authenticate(api_key: str):
    """Verify API key, return (session, agent). Raises ValueError if invalid."""
    from agentrelay.security.auth import verify_api_key

    factory = _get_session_factory()
    session = factory()
    agent = await verify_api_key(api_key, session)
    if agent is None:
        await session.close()
        raise ValueError("Invalid API key")
    return session, agent


def _task_to_dict(task) -> dict:
    return {
        "id": str(task.id),
        "task_spec": task.task_spec,
        "status": task.status,
        "publisher_id": str(task.publisher_id),
        "claimed_by": str(task.claimed_by) if task.claimed_by else None,
        "reward": task.reward,
        "deadline_at": task.deadline_at.isoformat() if task.deadline_at else None,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }


@mcp.tool()
async def list_tasks(api_key: str, limit: int = 50) -> list[dict]:
    """List available (open) tasks, ordered by creation date descending."""
    session, _agent = await _authenticate(api_key)
    try:
        from agentrelay.repositories.task_repo import TaskRepository
        from agentrelay.repositories.submission_repo import SubmissionRepository
        from agentrelay.services.task_service import TaskService

        svc = TaskService(TaskRepository(session), SubmissionRepository(session))
        tasks = await svc.get_available_tasks(limit=limit)
        return [_task_to_dict(t) for t in tasks]
    finally:
        await session.close()


@mcp.tool()
async def get_task(api_key: str, task_id: str) -> dict:
    """Get a single task by its UUID."""
    session, _agent = await _authenticate(api_key)
    try:
        from agentrelay.repositories.task_repo import TaskRepository

        task = await TaskRepository(session).get(uuid.UUID(task_id))
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        return _task_to_dict(task)
    finally:
        await session.close()


@mcp.tool()
async def create_task(
    api_key: str,
    task_spec: dict,
    reward: float = 0.0,
    deadline_seconds: int | None = None,
) -> dict:
    """Create a new task. The authenticated agent becomes the publisher."""
    session, agent = await _authenticate(api_key)
    try:
        from agentrelay.repositories.task_repo import TaskRepository
        from agentrelay.repositories.submission_repo import SubmissionRepository
        from agentrelay.services.task_service import TaskService
        from agentrelay.schemas.task import TaskCreate

        svc = TaskService(TaskRepository(session), SubmissionRepository(session))
        data = TaskCreate(
            task_spec=task_spec,
            publisher_id=agent.id,
            reward=reward,
            deadline_seconds=deadline_seconds,
        )
        task = await svc.create_task(data)
        await session.commit()
        return _task_to_dict(task)
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@mcp.tool()
async def claim_task(api_key: str, task_id: str) -> dict:
    """Claim an open task for the authenticated agent."""
    session, agent = await _authenticate(api_key)
    try:
        from agentrelay.repositories.task_repo import TaskRepository
        from agentrelay.repositories.submission_repo import SubmissionRepository
        from agentrelay.services.task_service import TaskService

        svc = TaskService(TaskRepository(session), SubmissionRepository(session))
        task = await svc.claim_task(uuid.UUID(task_id), agent.id)
        await session.commit()
        return _task_to_dict(task)
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@mcp.tool()
async def submit_task(api_key: str, task_id: str, output_data: dict) -> dict:
    """Submit output for a claimed task."""
    session, agent = await _authenticate(api_key)
    try:
        from agentrelay.repositories.task_repo import TaskRepository
        from agentrelay.repositories.submission_repo import SubmissionRepository
        from agentrelay.services.task_service import TaskService
        from agentrelay.schemas.submission import SubmissionCreate

        svc = TaskService(TaskRepository(session), SubmissionRepository(session))
        data = SubmissionCreate(
            task_id=uuid.UUID(task_id),
            agent_id=agent.id,
            output_data=output_data,
        )
        submission = await svc.submit_task(data)
        await session.commit()
        return {
            "id": str(submission.id),
            "task_id": str(submission.task_id),
            "agent_id": str(submission.agent_id),
            "output_data": submission.output_data,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        }
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@mcp.tool()
async def get_agent_reputation(api_key: str, agent_id: str) -> dict:
    """Get the latest reputation snapshot for an agent."""
    session, _agent = await _authenticate(api_key)
    try:
        from agentrelay.repositories.reputation_repo import ReputationRepository

        snapshot = await ReputationRepository(session).get_latest(uuid.UUID(agent_id))
        if snapshot is None:
            return {"agent_id": agent_id, "metrics": None, "message": "No reputation data yet"}
        return {
            "agent_id": agent_id,
            "metrics": snapshot.metrics,
            "snapshot_at": snapshot.snapshot_at.isoformat() if snapshot.snapshot_at else None,
        }
    finally:
        await session.close()


if __name__ == "__main__":
    mcp.run()
