from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)

    def merge(self, other: ValidationResult) -> ValidationResult:
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
        )


class BaseValidator(ABC):
    @abstractmethod
    def validate(
        self,
        input_data: dict,
        output_data: dict,
        schema: dict,
    ) -> ValidationResult: ...
