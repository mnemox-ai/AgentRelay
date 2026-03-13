"""Validation service — runs automated validation pipeline on submissions."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from agentrelay.domain.validation_result import ValidationResult, ValidatorType
from agentrelay.models.validation_run import ValidationRun
from agentrelay.validation.schema_validator import SchemaValidator
from agentrelay.validation.rule_validator import RuleValidator


class ValidationService:
    def __init__(self, session: AsyncSession | None = None) -> None:
        self.schema_validator = SchemaValidator()
        self.rule_validator = RuleValidator()
        self.session = session

    async def validate_submission(
        self,
        submission,
        task,
    ) -> ValidationResult:
        """Run validation pipeline based on task_spec.validation_method.

        Dispatches validators according to validation_method:
          - "schema"       → schema only
          - "schema+rule"  → schema then rule
          - "schema+test"  → schema then test (test not yet implemented, skipped)

        Each validator result is persisted as a ValidationRun row.
        Returns the merged ValidationResult with overall pass/fail and score.
        """
        task_spec = task.task_spec or {}
        output_schema = task_spec.get("output_schema", {})
        validation_method = task_spec.get("validation_method", "schema+rule")
        input_data = task_spec.get("input_data", {})
        output_data = submission.output_data or {}

        results: list[ValidationResult] = []

        # Step 1: Schema validation (always runs)
        schema_result = self.schema_validator.validate(input_data, output_data, output_schema)
        results.append(schema_result)
        await self._persist_run(submission.id, schema_result)

        # Short-circuit if schema fails
        if not schema_result.passed:
            return self._merge_results(results)

        # Step 2: Dispatch based on validation_method
        if validation_method == "schema+rule":
            rule_result = self.rule_validator.validate(input_data, output_data, output_schema)
            results.append(rule_result)
            await self._persist_run(submission.id, rule_result)
        elif validation_method == "schema+test":
            # Test validator not yet implemented — record a pass-through
            test_result = ValidationResult(
                passed=True,
                score=1.0,
                validator_type=ValidatorType.TEST,
                details="test validator not yet implemented, skipped",
            )
            results.append(test_result)
            await self._persist_run(submission.id, test_result)
        # "schema" → no additional validators

        return self._merge_results(results)

    async def _persist_run(self, submission_id, result: ValidationResult) -> None:
        """Save a ValidationRun record to the database."""
        if self.session is None:
            return
        run = ValidationRun(
            submission_id=submission_id,
            validator_type=result.validator_type.value,
            passed=result.passed,
            score=result.score,
            details={
                "details": result.details,
                "errors": result.errors,
            },
        )
        self.session.add(run)
        await self.session.flush()

    @staticmethod
    def _merge_results(results: list[ValidationResult]) -> ValidationResult:
        """Merge multiple ValidationResults into a single aggregate result."""
        return ValidationResult.merge(*results)
