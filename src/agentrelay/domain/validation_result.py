"""Validation result domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class ValidatorType(Enum):
    SCHEMA = "schema"
    RULE = "rule"
    TEST = "test"
    CONSENSUS = "consensus"
    LLM_JUDGE = "llm_judge"


@dataclass
class ValidationResult:
    passed: bool
    score: float
    validator_type: ValidatorType
    details: str
    validated_at: datetime = None

    def __post_init__(self) -> None:
        if self.validated_at is None:
            self.validated_at = datetime.now(timezone.utc)
