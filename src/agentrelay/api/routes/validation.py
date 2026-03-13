"""Validation result lookup routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.api.deps import get_db
from agentrelay.models.validation_run import ValidationRun

router = APIRouter(tags=["validation"])


@router.get("/submissions/{submission_id}/validation")
async def get_validation(submission_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(ValidationRun).where(ValidationRun.submission_id == submission_id)
    result = await db.execute(stmt)
    runs = list(result.scalars().all())
    if not runs:
        raise HTTPException(status_code=404, detail="No validation results found")
    return [
        {
            "id": str(run.id),
            "submission_id": str(run.submission_id),
            "validator_type": run.validator_type,
            "passed": run.passed,
            "score": run.score,
            "details": run.details,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }
        for run in runs
    ]
