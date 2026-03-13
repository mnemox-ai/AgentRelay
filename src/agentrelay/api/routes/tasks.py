"""Task CRUD, claim, and submit routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.api.deps import get_db
from agentrelay.repositories.submission_repo import SubmissionRepository
from agentrelay.repositories.task_repo import TaskRepository
from agentrelay.schemas.submission import SubmissionCreate, SubmissionResponse
from agentrelay.schemas.task import TaskClaimRequest, TaskCreate, TaskResponse
from agentrelay.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _task_service(db: AsyncSession) -> TaskService:
    return TaskService(TaskRepository(db), SubmissionRepository(db))


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    svc = _task_service(db)
    task = await svc.create_task(body)
    return task


@router.get("/available", response_model=list[TaskResponse])
async def list_available_tasks(limit: int = 50, db: AsyncSession = Depends(get_db)):
    svc = _task_service(db)
    return await svc.get_available_tasks(limit=limit)


@router.post("/{task_id}/claim", response_model=TaskResponse)
async def claim_task(task_id: uuid.UUID, body: TaskClaimRequest, db: AsyncSession = Depends(get_db)):
    svc = _task_service(db)
    try:
        task = await svc.claim_task(task_id, body.agent_id)
        await db.refresh(task)
        return task
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/{task_id}/submit", response_model=SubmissionResponse)
async def submit_task(task_id: uuid.UUID, body: SubmissionCreate, db: AsyncSession = Depends(get_db)):
    svc = _task_service(db)
    try:
        submission = await svc.submit_task(body)
        await db.refresh(submission)
        return submission
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
