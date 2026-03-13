"""Validation run response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ValidationRunResponse(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    validator_type: str
    passed: bool
    score: float
    details: dict[str, Any]
    validated_at: datetime = Field(validation_alias="created_at")

    model_config = {"from_attributes": True, "populate_by_name": True}
