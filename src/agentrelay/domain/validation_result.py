"""Validation result domain objects."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    errors: list[str] = field(default_factory=list)
    validated_at: datetime = None

    def __post_init__(self) -> None:
        if self.validated_at is None:
            self.validated_at = datetime.now(timezone.utc)

    @classmethod
    def merge(cls, *results: ValidationResult) -> ValidationResult:
        """Merge multiple ValidationResults. passed=AND of all, errors=concatenated."""
        if not results:
            return cls(
                passed=True,
                score=0.0,
                validator_type=ValidatorType.SCHEMA,
                details="",
            )
        passed = all(r.passed for r in results)
        all_errors: list[str] = []
        for r in results:
            all_errors.extend(r.errors)
        score = min(r.score for r in results)
        details = "; ".join(r.details for r in results if r.details)
        return cls(
            passed=passed,
            score=score,
            validator_type=results[0].validator_type,
            details=details,
            errors=all_errors,
        )
