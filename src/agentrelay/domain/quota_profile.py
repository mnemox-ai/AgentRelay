"""Quota profile domain objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QuotaProfile:
    provider: str
    model: str
    executor_type: str
    plan_type: str
    daily_task_budget: int
    safe_token_cap: int
