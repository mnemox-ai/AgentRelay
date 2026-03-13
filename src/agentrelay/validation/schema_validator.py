from __future__ import annotations

import jsonschema

from agentrelay.domain.validation_result import ValidationResult, ValidatorType

from .base import BaseValidator


class SchemaValidator(BaseValidator):
    """Validates output_data against a JSON Schema."""

    def validate(
        self,
        input_data: dict,
        output_data: dict,
        schema: dict,
    ) -> ValidationResult:
        errors: list[str] = []
        validator = jsonschema.Draft7Validator(schema)
        for error in sorted(validator.iter_errors(output_data), key=lambda e: list(e.path)):
            path = ".".join(str(p) for p in error.absolute_path) or "(root)"
            errors.append(f"{path}: {error.message}")
        passed = len(errors) == 0
        return ValidationResult(
            passed=passed,
            score=1.0 if passed else 0.0,
            validator_type=ValidatorType.SCHEMA,
            details="" if passed else f"{len(errors)} schema error(s)",
            errors=errors,
        )
