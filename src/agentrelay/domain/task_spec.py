"""Task specification domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskType(Enum):
    DATA_STRUCTURING = "data_structuring"
    RESEARCH_EXTRACTION = "research_extraction"
    CODING = "coding"
    CONTENT_GENERATION = "content_generation"
    CLASSIFICATION = "classification"


class TaskStatus(Enum):
    OPEN = "open"
    CLAIMED = "claimed"
    SUBMITTED = "submitted"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class TaskDifficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class TaskSpec:
    task_type: TaskType
    input_data: dict[str, Any]
    output_schema: dict[str, Any]
    validation_method: str
    difficulty: TaskDifficulty
    token_estimate: int
    reward: float
    deadline_seconds: int
    allowed_models: list[str] = field(default_factory=list)
