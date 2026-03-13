"""Dashboard response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_tasks: int
    completed_tasks: int
    active_agents: int
    total_rewards: float


class RecentTask(BaseModel):
    id: uuid.UUID
    task_spec: dict[str, Any]
    status: str
    reward: float
    created_at: datetime
    agent_name: str | None = None
    validation_score: float | None = None


class TopAgent(BaseModel):
    id: uuid.UUID
    name: str
    quality_score: float
    total_submissions: int
    pass_rate: float


class ValidationRate(BaseModel):
    passed: int
    total: int
    rate: float


class LedgerEntryResponse(BaseModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    task_id: uuid.UUID | None = None
    amount: float
    entry_type: str
    created_at: datetime

    model_config = {"from_attributes": True}
