"""Reputation request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ReputationResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    metrics: dict[str, Any]
    snapshot_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
