"""Submission request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class SubmissionCreate(BaseModel):
    task_id: uuid.UUID
    agent_id: uuid.UUID
    output_data: dict[str, Any]


class SubmissionResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    agent_id: uuid.UUID
    output_data: dict[str, Any]
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
