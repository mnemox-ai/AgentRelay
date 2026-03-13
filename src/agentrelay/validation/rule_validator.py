from __future__ import annotations

from typing import Callable

from agentrelay.domain.validation_result import ValidationResult, ValidatorType

from .base import BaseValidator

# Type alias for a rule function
Rule = Callable[[dict, dict, dict], list[str]]


def required_fields_present(
    input_data: dict,
    output_data: dict,
    schema: dict,
) -> list[str]:
    """Check that all required fields from the schema exist in output_data."""
    required = schema.get("required", [])
    return [f"missing required field: {f}" for f in required if f not in output_data]


def no_empty_values(
    input_data: dict,
    output_data: dict,
    schema: dict,
) -> list[str]:
    """Check that no field in output_data has an empty value (None, '', [], {})."""
    errors: list[str] = []
    for key, value in output_data.items():
        if value is None or value == "" or value == [] or value == {}:
            errors.append(f"empty value for field: {key}")
    return errors


def type_check(
    input_data: dict,
    output_data: dict,
    schema: dict,
) -> list[str]:
    """Check that field types match the schema's 'properties' type declarations."""
    _TYPE_MAP: dict[str, type | tuple[type, ...]] = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    properties = schema.get("properties", {})
    errors: list[str] = []
    for key, prop in properties.items():
        if key not in output_data:
            continue
        expected_type_str = prop.get("type")
        if expected_type_str is None:
            continue
        expected = _TYPE_MAP.get(expected_type_str)
        if expected is None:
            continue
        value = output_data[key]
        if not isinstance(value, expected):
            errors.append(
                f"field '{key}' expected type {expected_type_str}, got {type(value).__name__}"
            )
    return errors


# Built-in rules
DEFAULT_RULES: list[Rule] = [
    required_fields_present,
    no_empty_values,
    type_check,
]


class RuleValidator(BaseValidator):
    """Extensible rule engine validator."""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules = rules if rules is not None else list(DEFAULT_RULES)

    def add_rule(self, rule: Rule) -> None:
        self.rules.append(rule)

    def validate(
        self,
        input_data: dict,
        output_data: dict,
        schema: dict,
    ) -> ValidationResult:
        errors: list[str] = []
        for rule in self.rules:
            errors.extend(rule(input_data, output_data, schema))
        passed = len(errors) == 0
        return ValidationResult(
            passed=passed,
            score=1.0 if passed else 0.0,
            validator_type=ValidatorType.RULE,
            details="" if passed else f"{len(errors)} rule error(s)",
            errors=errors,
        )
