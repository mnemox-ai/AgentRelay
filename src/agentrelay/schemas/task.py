"""Task request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    task_spec: dict[str, Any]
    publisher_id: uuid.UUID
    reward: float = 0.0
    deadline_seconds: int | None = None


class TaskClaimRequest(BaseModel):
    agent_id: uuid.UUID


class TaskResponse(BaseModel):
    id: uuid.UUID
    task_spec: dict[str, Any]
    status: str
    publisher_id: uuid.UUID
    claimed_by: uuid.UUID | None = None
    reward: float
    deadline_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
