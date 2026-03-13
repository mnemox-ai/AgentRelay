"""Tests for automated validation pipeline — end-to-end through the service layer."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from agentrelay.domain.validation_result import ValidatorType
from agentrelay.services.validation_service import ValidationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCHEMA = {
    "type": "object",
    "required": ["name", "score"],
    "properties": {
        "name": {"type": "string"},
        "score": {"type": "integer"},
    },
}


def _sub_task(output_data, output_schema=None, validation_method="schema+rule"):
    """Build mock submission + task for pipeline tests."""
    sub = MagicMock()
    sub.id = uuid.uuid4()
    sub.output_data = output_data
    task = MagicMock()
    task.task_spec = {
        "output_schema": output_schema or SCHEMA,
        "validation_method": validation_method,
        "input_data": {},
    }
    return sub, task


# ---------------------------------------------------------------------------
# Schema-only pipeline
# ---------------------------------------------------------------------------

class TestSchemaOnlyPipeline:
    @pytest.mark.asyncio
    async def test_schema_only_pass(self):
        """Schema-only: valid output passes with score 1.0."""
        sub, task = _sub_task({"name": "Alice", "score": 42}, validation_method="schema")
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        assert result.passed is True
        assert result.score == 1.0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_schema_only_fail(self):
        """Schema-only: invalid output fails."""
        sub, task = _sub_task({"name": 123, "score": "bad"}, validation_method="schema")
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        assert result.passed is False
        assert result.score == 0.0
        assert len(result.errors) > 0
        assert result.validator_type == ValidatorType.SCHEMA

    @pytest.mark.asyncio
    async def test_schema_only_does_not_run_rules(self):
        """Schema-only: empty string passes schema but rule validator is NOT run."""
        sub, task = _sub_task({"name": "", "score": 42}, validation_method="schema")
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        # Schema allows empty strings, rule validator would flag it but it's not run
        assert result.passed is True


# ---------------------------------------------------------------------------
# Schema + Rule pipeline
# ---------------------------------------------------------------------------

class TestSchemaRulePipeline:
    @pytest.mark.asyncio
    async def test_schema_rule_pass(self):
        """Schema+rule: valid output passes both validators."""
        sub, task = _sub_task({"name": "Alice", "score": 42}, validation_method="schema+rule")
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        assert result.passed is True
        assert result.score == 1.0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_schema_fail_short_circuits_rule(self):
        """Schema+rule: schema failure short-circuits — rule validator does not run."""
        sub, task = _sub_task({"name": 123, "score": "bad"}, validation_method="schema+rule")
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        assert result.passed is False
        assert result.score == 0.0
        # Only schema errors, no rule errors
        assert result.validator_type == ValidatorType.SCHEMA

    @pytest.mark.asyncio
    async def test_rule_fail_but_schema_pass(self):
        """Schema+rule: output passes schema but fails rule validation (empty value)."""
        sub, task = _sub_task({"name": "", "score": 42}, validation_method="schema+rule")
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        assert result.passed is False
        assert result.score == 0.0
        assert any("empty" in e for e in result.errors)

    @pytest.mark.asyncio
    async def test_missing_required_field(self):
        """Schema+rule: missing required field fails at schema level."""
        sub, task = _sub_task({"name": "Alice"}, validation_method="schema+rule")
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        assert result.passed is False
        assert any("score" in e for e in result.errors)


# ---------------------------------------------------------------------------
# Schema + Test pipeline (test validator not yet implemented)
# ---------------------------------------------------------------------------

class TestSchemaTestPipeline:
    @pytest.mark.asyncio
    async def test_schema_test_pass(self):
        """Schema+test: valid output passes; test validator is a pass-through."""
        sub, task = _sub_task({"name": "Alice", "score": 42}, validation_method="schema+test")
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        assert result.passed is True
        assert result.score == 1.0


# ---------------------------------------------------------------------------
# Validation result structure
# ---------------------------------------------------------------------------

class TestValidationResultDetails:
    @pytest.mark.asyncio
    async def test_merged_result_contains_details(self):
        """Merged result joins details from all validators."""
        sub, task = _sub_task({"name": "", "score": 42}, validation_method="schema+rule")
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        # Schema passed → empty details; Rule failed → has details
        assert "rule error" in result.details

    @pytest.mark.asyncio
    async def test_schema_fail_details(self):
        """Schema failure result includes error count in details."""
        sub, task = _sub_task({"name": 123}, validation_method="schema")
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        assert "schema error" in result.details
        assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# Persistence of validation runs (with mock session)
# ---------------------------------------------------------------------------

class TestValidationRunPersistence:
    @pytest.mark.asyncio
    async def test_schema_only_persists_one_run(self):
        """Schema-only: exactly 1 ValidationRun is persisted."""
        from unittest.mock import AsyncMock

        session = AsyncMock()
        svc = ValidationService(session=session)
        sub, task = _sub_task({"name": "Alice", "score": 42}, validation_method="schema")
        await svc.validate_submission(sub, task)

        # session.add called once, session.flush called once
        assert session.add.call_count == 1
        assert session.flush.call_count == 1

    @pytest.mark.asyncio
    async def test_schema_rule_persists_two_runs(self):
        """Schema+rule pass: exactly 2 ValidationRuns are persisted."""
        from unittest.mock import AsyncMock

        session = AsyncMock()
        svc = ValidationService(session=session)
        sub, task = _sub_task({"name": "Alice", "score": 42}, validation_method="schema+rule")
        await svc.validate_submission(sub, task)

        assert session.add.call_count == 2
        assert session.flush.call_count == 2

    @pytest.mark.asyncio
    async def test_schema_fail_persists_one_run(self):
        """Schema fail short-circuits: only 1 ValidationRun persisted."""
        from unittest.mock import AsyncMock

        session = AsyncMock()
        svc = ValidationService(session=session)
        sub, task = _sub_task({"name": 123}, validation_method="schema+rule")
        await svc.validate_submission(sub, task)

        assert session.add.call_count == 1
        assert session.flush.call_count == 1

    @pytest.mark.asyncio
    async def test_persisted_run_has_correct_fields(self):
        """Persisted ValidationRun has correct validator_type, passed, score, details."""
        from unittest.mock import AsyncMock
        from agentrelay.models.validation_run import ValidationRun

        session = AsyncMock()
        svc = ValidationService(session=session)
        sub, task = _sub_task({"name": "Alice", "score": 42}, validation_method="schema")
        await svc.validate_submission(sub, task)

        run = session.add.call_args[0][0]
        assert isinstance(run, ValidationRun)
        assert run.validator_type == "schema"
        assert run.passed is True
        assert run.score == 1.0
        assert run.submission_id == sub.id
        assert "details" in run.details
        assert "errors" in run.details


# ---------------------------------------------------------------------------
# Default validation_method fallback
# ---------------------------------------------------------------------------

class TestDefaultValidationMethod:
    @pytest.mark.asyncio
    async def test_defaults_to_schema_rule(self):
        """When validation_method is missing from task_spec, defaults to schema+rule."""
        sub = MagicMock()
        sub.id = uuid.uuid4()
        sub.output_data = {"name": "", "score": 42}
        task = MagicMock()
        task.task_spec = {
            "output_schema": SCHEMA,
            "input_data": {},
            # no validation_method key
        }
        svc = ValidationService()
        result = await svc.validate_submission(sub, task)

        # Empty string fails rule validation (no_empty_values)
        assert result.passed is False
        assert any("empty" in e for e in result.errors)
