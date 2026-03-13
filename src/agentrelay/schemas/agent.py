"""Agent request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class AgentRegister(BaseModel):
    name: str
    quota_profile: dict[str, Any] = {}
    capabilities: dict[str, Any] = {}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        import re

        if len(v) < 3:
            raise ValueError("name must be at least 3 characters")
        if len(v) > 255:
            raise ValueError("name must be at most 255 characters")
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", v):
            raise ValueError("name must contain only alphanumeric characters, hyphens, and underscores")
        return v


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    quota_profile: dict[str, Any]
    capabilities: dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
