"""Validation result lookup routes."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.api.deps import get_db
from agentrelay.schemas.validation import ValidationRunResponse
from agentrelay.services.validation_service import ValidationService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["validation"])


@router.get(
    "/submissions/{submission_id}/validation",
    response_model=list[ValidationRunResponse],
)
async def get_validation(submission_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    try:
        svc = ValidationService(session=db)
        runs = await svc.get_validation_runs(submission_id)
        if not runs:
            raise HTTPException(status_code=404, detail="No validation results found")
        return runs
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error fetching validation for submission %s", submission_id)
        raise
