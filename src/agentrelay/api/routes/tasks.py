"""Task CRUD, claim, and submit routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.api.deps import get_db, rate_limit_by_agent, rate_limit_by_ip
from agentrelay.domain.task_lifecycle import InvalidTransitionError
from agentrelay.models.agent import Agent
from agentrelay.repositories.submission_repo import SubmissionRepository
from agentrelay.repositories.task_repo import TaskRepository
from agentrelay.repositories.agent_repo import AgentRepository
from agentrelay.schemas.submission import SubmissionCreate, SubmissionResponse
from agentrelay.schemas.task import TaskClaimRequest, TaskCreate, TaskResponse
from agentrelay.security.task_sanitizer import scan_input
from agentrelay.security.output_sanitizer import scan_output
from agentrelay.security.token_limiter import check_token_budget
from agentrelay.repositories.ledger_repo import LedgerRepository
from agentrelay.repositories.reputation_repo import ReputationRepository
from agentrelay.services.ledger_service import LedgerService
from agentrelay.services.reputation_service import ReputationService
from agentrelay.services.task_service import TaskService
from agentrelay.services.expiration_service import expire_overdue_tasks
from agentrelay.services.validation_service import ValidationService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _collect_strings(obj: object) -> list[str]:
    """Recursively collect all string values from a nested structure."""
    if isinstance(obj, str):
        return [obj]
    if isinstance(obj, dict):
        parts: list[str] = []
        for v in obj.values():
            parts.extend(_collect_strings(v))
        return parts
    if isinstance(obj, (list, tuple)):
        parts = []
        for item in obj:
            parts.extend(_collect_strings(item))
        return parts
    return []


def _task_service(db: AsyncSession, with_agent_repo: bool = False) -> TaskService:
    agent_repo = AgentRepository(db) if with_agent_repo else None
    return TaskService(TaskRepository(db), SubmissionRepository(db), agent_repo=agent_repo)


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    _agent: Agent = Depends(rate_limit_by_agent),
    db: AsyncSession = Depends(get_db),
):
    # Scan task_spec for prompt injection
    text_to_scan = " ".join(_collect_strings(body.task_spec))
    if text_to_scan.strip():
        scan_result = scan_input(text_to_scan)
        if not scan_result.clean:
            raise HTTPException(
                status_code=400,
                detail=f"Task input blocked by security scanner: {scan_result.flagged_patterns}",
            )

    svc = _task_service(db)
    task = await svc.create_task(body)
    return task


@router.get("/available", response_model=list[TaskResponse], dependencies=[Depends(rate_limit_by_ip)])
async def list_available_tasks(
    limit: int = 50,
    agent_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    if agent_id is not None:
        svc = _task_service(db, with_agent_repo=True)
        try:
            return await svc.match_tasks_for_agent(agent_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
    svc = _task_service(db)
    return await svc.get_available_tasks(limit=limit)


@router.get("/{task_id}", response_model=TaskResponse, dependencies=[Depends(rate_limit_by_ip)])
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    repo = TaskRepository(db)
    task = await repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/{task_id}/claim", response_model=TaskResponse)
async def claim_task(
    task_id: uuid.UUID,
    body: TaskClaimRequest,
    _agent: Agent = Depends(rate_limit_by_agent),
    db: AsyncSession = Depends(get_db),
):
    # Check token budget before allowing claim
    task_repo = TaskRepository(db)
    task = await task_repo.get(task_id)
    if task is not None:
        token_estimate = (task.task_spec or {}).get("token_estimate", 0)
        if token_estimate > 0:
            agent_repo = AgentRepository(db)
            quota = await agent_repo.get_quota_profile(body.agent_id)
            if quota is not None:
                if not check_token_budget(token_estimate, quota.safe_token_cap):
                    raise HTTPException(
                        status_code=403,
                        detail=f"Token budget exceeded: task requires {token_estimate} tokens but agent cap is {quota.safe_token_cap}",
                    )

    svc = _task_service(db)
    try:
        task = await svc.claim_task(task_id, body.agent_id)
        await db.refresh(task)
        return task
    except (ValueError, InvalidTransitionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{task_id}/submit", response_model=SubmissionResponse)
async def submit_task(
    task_id: uuid.UUID,
    body: SubmissionCreate,
    _agent: Agent = Depends(rate_limit_by_agent),
    db: AsyncSession = Depends(get_db),
):
    # Scan output_data for malicious content
    text_to_scan = " ".join(_collect_strings(body.output_data))
    if text_to_scan.strip():
        scan_result = scan_output(text_to_scan)
        if not scan_result.clean:
            raise HTTPException(
                status_code=400,
                detail=f"Output blocked by security scanner: {scan_result.flagged_patterns}",
            )

    svc = _task_service(db)
    task_repo = TaskRepository(db)
    try:
        submission = await svc.submit_task(body)

        # Transition to validating
        task = await task_repo.get(body.task_id)
        await task_repo.update_status(body.task_id, "validating")

        # Run automated validation pipeline
        validation_svc = ValidationService(session=db)
        result = await validation_svc.validate_submission(submission, task)

        # Update task status based on validation outcome
        final_status = "completed" if result.passed else "failed"
        await task_repo.update_status(body.task_id, final_status)

        # Post-validation: ledger + reputation updates
        ledger_svc = LedgerService(LedgerRepository(db))
        reputation_svc = ReputationService(ReputationRepository(db))

        if result.passed:
            await ledger_svc.record_reward(body.agent_id, body.task_id, task.reward)
        else:
            await ledger_svc.record_penalty(body.agent_id, body.task_id, task.reward)

        await reputation_svc.update_reputation(body.agent_id, result)

        await db.refresh(submission)
        return submission
    except (ValueError, InvalidTransitionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/expire", status_code=200, dependencies=[Depends(rate_limit_by_ip)])
async def expire_tasks(db: AsyncSession = Depends(get_db)):
    """Expire all overdue tasks. Intended for admin/cron trigger."""
    expired = await expire_overdue_tasks(db)
    return {"expired_count": len(expired), "expired": expired}
