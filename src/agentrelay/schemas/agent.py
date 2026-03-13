"""Agent request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AgentRegister(BaseModel):
    name: str
    quota_profile: dict[str, Any] = {}
    capabilities: dict[str, Any] = {}


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    quota_profile: dict[str, Any]
    capabilities: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
