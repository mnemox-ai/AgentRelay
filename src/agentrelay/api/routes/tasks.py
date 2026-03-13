"""Task CRUD, claim, and submit routes."""

from __future__ import annotations

import logging
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
from agentrelay.schemas.task import TaskBatchCreate, TaskClaimRequest, TaskCreate, TaskResponse
from agentrelay.security.task_sanitizer import scan_input
from agentrelay.security.output_sanitizer import scan_output
from agentrelay.repositories.ledger_repo import LedgerRepository
from agentrelay.repositories.reputation_repo import ReputationRepository
from agentrelay.services.ledger_service import LedgerService
from agentrelay.services.reputation_service import ReputationService
from agentrelay.services.task_service import TaskService
from agentrelay.services.quota_service import QuotaExceededError, QuotaService
from agentrelay.services.expiration_service import expire_overdue_tasks
from agentrelay.services.notification_service import notification_service
from agentrelay.services.validation_service import ValidationService
from agentrelay.services.queue_service import QueueService, get_redis
from agentrelay.domain.task_spec import TaskStatus
from agentrelay.config import settings

logger = logging.getLogger(__name__)

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
    await notification_service.broadcast("task_created", {"task_id": str(task.id), "status": task.status})
    return task


@router.post("/batch", response_model=list[TaskResponse], status_code=201)
async def create_tasks_batch(
    body: TaskBatchCreate,
    _agent: Agent = Depends(rate_limit_by_agent),
    db: AsyncSession = Depends(get_db),
):
    if len(body.tasks) > settings.BATCH_MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size exceeds maximum of {settings.BATCH_MAX_SIZE}",
        )

    # Scan all task specs for prompt injection
    for item in body.tasks:
        text_to_scan = " ".join(_collect_strings(item.task_spec))
        if text_to_scan.strip():
            scan_result = scan_input(text_to_scan)
            if not scan_result.clean:
                raise HTTPException(
                    status_code=400,
                    detail=f"Task input blocked by security scanner: {scan_result.flagged_patterns}",
                )

    svc = _task_service(db)
    tasks = await svc.create_tasks_batch(body.tasks)

    # Enqueue into Redis priority queue (best-effort)
    try:
        redis_client = await get_redis()
        try:
            queue_svc = QueueService(redis_client)
            queue_items = []
            for task in tasks:
                token_estimate = (task.task_spec or {}).get("token_estimate", 0)
                queue_items.append({
                    "task_id": task.id,
                    "reward": task.reward,
                    "token_estimate": token_estimate,
                    "deadline_at": task.deadline_at,
                })
            await queue_svc.enqueue_batch(queue_items)
        finally:
            await redis_client.aclose()
    except Exception:
        logger.warning("Redis unavailable during batch enqueue — tasks are still in DB")

    for task in tasks:
        await notification_service.broadcast("task_created", {"task_id": str(task.id), "status": task.status})

    return tasks


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

    # Try Redis priority queue first, fallback to DB
    try:
        redis_client = await get_redis()
        try:
            queue_svc = QueueService(redis_client)
            task_ids = await queue_svc.top_n(limit)
            if task_ids:
                repo = TaskRepository(db)
                tasks = []
                for tid in task_ids:
                    task = await repo.get(uuid.UUID(tid))
                    if task is not None and task.status == TaskStatus.OPEN.value:
                        tasks.append(task)
                if tasks:
                    return tasks
        finally:
            await redis_client.aclose()
    except Exception:
        logger.warning("Redis unavailable — falling back to DB for available tasks")

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
    # Check quota (token cap + daily budget) before allowing claim
    task_repo = TaskRepository(db)
    task = await task_repo.get(task_id)
    if task is not None:
        agent_repo = AgentRepository(db)
        quota_svc = QuotaService(task_repo=task_repo, agent_repo=agent_repo)
        try:
            await quota_svc.check_and_deduct_quota(body.agent_id, task)
        except QuotaExceededError as exc:
            raise HTTPException(status_code=403, detail=str(exc))

    svc = _task_service(db)
    try:
        task = await svc.claim_task(task_id, body.agent_id)
        await db.refresh(task)
        await notification_service.broadcast("task_claimed", {"task_id": str(task.id), "status": task.status, "agent_id": str(body.agent_id)})
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
        await task_repo.update_status(body.task_id, TaskStatus.VALIDATING.value)

        # Run automated validation pipeline
        validation_svc = ValidationService(session=db)
        result = await validation_svc.validate_submission(submission, task)

        # Update task status based on validation outcome
        final_status = TaskStatus.COMPLETED.value if result.passed else TaskStatus.FAILED.value
        await task_repo.update_status(body.task_id, final_status)

        event_type = "task_completed" if result.passed else "task_failed"
        await notification_service.broadcast(event_type, {"task_id": str(body.task_id), "status": final_status})

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
