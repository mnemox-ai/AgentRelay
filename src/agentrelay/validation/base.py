from __future__ import annotations

from abc import ABC, abstractmethod

from agentrelay.domain.validation_result import ValidationResult, ValidatorType  # noqa: F401


class BaseValidator(ABC):
    @abstractmethod
    def validate(
        self,
        input_data: dict,
        output_data: dict,
        schema: dict,
    ) -> ValidationResult: ...
