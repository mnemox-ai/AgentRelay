"""Validation service — runs schema → rule pipeline on submissions."""

from __future__ import annotations

from agentrelay.validation.schema_validator import SchemaValidator
from agentrelay.validation.rule_validator import RuleValidator
from agentrelay.validation.base import ValidationResult


class ValidationService:
    def __init__(self) -> None:
        self.schema_validator = SchemaValidator()
        self.rule_validator = RuleValidator()

    def validate_submission(
        self,
        input_data: dict,
        output_data: dict,
        output_schema: dict,
    ) -> ValidationResult:
        schema_result = self.schema_validator.validate(input_data, output_data, output_schema)
        if not schema_result.valid:
            return schema_result
        rule_result = self.rule_validator.validate(input_data, output_data, output_schema)
        return schema_result.merge(rule_result)
