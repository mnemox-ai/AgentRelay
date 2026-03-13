"""Task CRUD, claim, and submit routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.api.deps import get_current_agent, get_db
from agentrelay.models.agent import Agent
from agentrelay.repositories.submission_repo import SubmissionRepository
from agentrelay.repositories.task_repo import TaskRepository
from agentrelay.repositories.agent_repo import AgentRepository
from agentrelay.schemas.submission import SubmissionCreate, SubmissionResponse
from agentrelay.schemas.task import TaskClaimRequest, TaskCreate, TaskResponse
from agentrelay.security.token_limiter import check_token_budget
from agentrelay.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_service(db: AsyncSession) -> TaskService:
    return TaskService(TaskRepository(db), SubmissionRepository(db))


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    body: TaskCreate,
    _agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    svc = _task_service(db)
    task = await svc.create_task(body)
    return task


@router.get("/available", response_model=list[TaskResponse])
async def list_available_tasks(limit: int = 50, db: AsyncSession = Depends(get_db)):
    svc = _task_service(db)
    return await svc.get_available_tasks(limit=limit)


@router.get("/{task_id}", response_model=TaskResponse)
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
    _agent: Agent = Depends(get_current_agent),
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
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{task_id}/submit", response_model=SubmissionResponse)
async def submit_task(
    task_id: uuid.UUID,
    body: SubmissionCreate,
    _agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    svc = _task_service(db)
    try:
        submission = await svc.submit_task(body)
        await db.refresh(submission)
        return submission
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
