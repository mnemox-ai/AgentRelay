"""Validation result lookup routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.api.deps import get_db
from agentrelay.models.validation_run import ValidationRun
from agentrelay.schemas.validation import ValidationRunResponse

router = APIRouter(tags=["validation"])


@router.get(
    "/submissions/{submission_id}/validation",
    response_model=list[ValidationRunResponse],
)
async def get_validation(submission_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = select(ValidationRun).where(ValidationRun.submission_id == submission_id)
    result = await db.execute(stmt)
    runs = list(result.scalars().all())
    if not runs:
        raise HTTPException(status_code=404, detail="No validation results found")
    return runs
