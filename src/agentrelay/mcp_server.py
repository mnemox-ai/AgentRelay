"""MCP Server for AgentRelay — exposes task CRUD + claim + submit as MCP tools."""

from __future__ import annotations

import logging
import uuid

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

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
    try:
        parsed_id = uuid.UUID(task_id)
    except ValueError:
        raise ValueError(f"Invalid task_id UUID: {task_id}")
    session, _agent = await _authenticate(api_key)
    try:
        from agentrelay.repositories.task_repo import TaskRepository

        task = await TaskRepository(session).get(parsed_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        return _task_to_dict(task)
    except ValueError:
        raise
    except Exception:
        logger.warning("DB error in get_task for %s", task_id, exc_info=True)
        raise
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
    except ValueError:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        logger.warning("DB error in create_task", exc_info=True)
        raise
    finally:
        await session.close()


@mcp.tool()
async def claim_task(api_key: str, task_id: str) -> dict:
    """Claim an open task for the authenticated agent."""
    try:
        parsed_id = uuid.UUID(task_id)
    except ValueError:
        raise ValueError(f"Invalid task_id UUID: {task_id}")
    session, agent = await _authenticate(api_key)
    try:
        from agentrelay.repositories.task_repo import TaskRepository
        from agentrelay.repositories.submission_repo import SubmissionRepository
        from agentrelay.services.task_service import TaskService

        svc = TaskService(TaskRepository(session), SubmissionRepository(session))
        task = await svc.claim_task(parsed_id, agent.id)
        await session.commit()
        return _task_to_dict(task)
    except ValueError:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        logger.warning("DB error in claim_task for %s", task_id, exc_info=True)
        raise
    finally:
        await session.close()


@mcp.tool()
async def submit_task(api_key: str, task_id: str, output_data: dict) -> dict:
    """Submit output for a claimed task."""
    try:
        parsed_id = uuid.UUID(task_id)
    except ValueError:
        raise ValueError(f"Invalid task_id UUID: {task_id}")
    session, agent = await _authenticate(api_key)
    try:
        from agentrelay.repositories.task_repo import TaskRepository
        from agentrelay.repositories.submission_repo import SubmissionRepository
        from agentrelay.services.task_service import TaskService
        from agentrelay.schemas.submission import SubmissionCreate

        svc = TaskService(TaskRepository(session), SubmissionRepository(session))
        data = SubmissionCreate(
            task_id=parsed_id,
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
    except ValueError:
        await session.rollback()
        raise
    except Exception:
        await session.rollback()
        logger.warning("DB error in submit_task for %s", task_id, exc_info=True)
        raise
    finally:
        await session.close()


@mcp.tool()
async def get_agent_reputation(api_key: str, agent_id: str) -> dict:
    """Get the latest reputation snapshot for an agent."""
    try:
        parsed_agent_id = uuid.UUID(agent_id)
    except ValueError:
        raise ValueError(f"Invalid agent_id UUID: {agent_id}")
    session, _agent = await _authenticate(api_key)
    try:
        from agentrelay.repositories.reputation_repo import ReputationRepository

        snapshot = await ReputationRepository(session).get_latest(parsed_agent_id)
        if snapshot is None:
            return {"agent_id": agent_id, "metrics": None, "message": "No reputation data yet"}
        return {
            "agent_id": agent_id,
            "metrics": snapshot.metrics,
            "snapshot_at": snapshot.snapshot_at.isoformat() if snapshot.snapshot_at else None,
        }
    except ValueError:
        raise
    except Exception:
        logger.warning("DB error in get_agent_reputation for %s", agent_id, exc_info=True)
        raise
    finally:
        await session.close()


_VERSION = "0.6.0"


@mcp.tool()
async def discover_capabilities() -> dict:
    """Discover AgentRelay system capabilities: supported task types, difficulties,
    validation methods, open task statistics, and server status. No auth required."""
    from agentrelay.domain.task_spec import TaskType, TaskDifficulty
    from agentrelay.domain.validation_result import ValidatorType
    from sqlalchemy import func, select

    task_types = [t.value for t in TaskType]
    difficulties = [d.value for d in TaskDifficulty]
    validation_methods = ["schema", "schema+rule", "schema+test"]
    validator_types = [v.value for v in ValidatorType]

    # Query open task stats
    open_tasks_by_type: dict[str, int] = {}
    open_tasks_by_difficulty: dict[str, int] = {}
    total_open = 0

    try:
        factory = _get_session_factory()
        async with factory() as session:
            from agentrelay.models.task import Task

            # Count open tasks by type
            rows = (
                await session.execute(
                    select(Task.task_spec, func.count())
                    .where(Task.status == "open")
                    .group_by(Task.task_spec)
                )
            ).all()

            for task_spec_json, count in rows:
                total_open += count
                if isinstance(task_spec_json, dict):
                    tt = task_spec_json.get("task_type", "unknown")
                    diff = task_spec_json.get("difficulty", "unknown")
                    open_tasks_by_type[tt] = open_tasks_by_type.get(tt, 0) + count
                    open_tasks_by_difficulty[diff] = open_tasks_by_difficulty.get(diff, 0) + count
    except Exception:
        logger.warning("DB unavailable in discover_capabilities — returning static info only", exc_info=True)

    return {
        "version": _VERSION,
        "status": "running",
        "task_types": task_types,
        "difficulties": difficulties,
        "validation_methods": validation_methods,
        "validator_types": validator_types,
        "open_tasks": {
            "total": total_open,
            "by_type": open_tasks_by_type,
            "by_difficulty": open_tasks_by_difficulty,
        },
    }


@mcp.resource("agentrelay://status")
async def server_status() -> str:
    """AgentRelay server info and task statistics."""
    import json

    info = await discover_capabilities()
    return json.dumps(info, indent=2)


if __name__ == "__main__":
    mcp.run()
