from __future__ import annotations

import jsonschema

from .base import BaseValidator, ValidationResult


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
        return ValidationResult(valid=len(errors) == 0, errors=errors)
