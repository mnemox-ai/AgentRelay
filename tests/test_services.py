"""Tests for service layer using mock repositories."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentrelay.domain.quota_profile import QuotaProfile
from agentrelay.domain.task_lifecycle import InvalidTransitionError
from agentrelay.schemas.submission import SubmissionCreate
from agentrelay.schemas.task import TaskCreate
from agentrelay.services.quota_service import QuotaService
from agentrelay.services.reputation_service import ReputationService
from agentrelay.services.task_service import TaskService
from agentrelay.services.validation_service import ValidationService
from agentrelay.domain.validation_result import ValidationResult, ValidatorType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(
    task_id=None,
    status="open",
    publisher_id=None,
    claimed_by=None,
    task_spec=None,
    reward=1.0,
):
    task = MagicMock()
    task.id = task_id or uuid.uuid4()
    task.status = status
    task.publisher_id = publisher_id or uuid.uuid4()
    task.claimed_by = claimed_by
    task.task_spec = task_spec or {"type": "coding"}
    task.reward = reward
    task.deadline_at = None
    task.created_at = datetime.now(timezone.utc)
    task.updated_at = datetime.now(timezone.utc)
    return task


def _make_submission(task_id=None, agent_id=None, output_data=None):
    sub = MagicMock()
    sub.id = uuid.uuid4()
    sub.task_id = task_id or uuid.uuid4()
    sub.agent_id = agent_id or uuid.uuid4()
    sub.output_data = output_data or {"result": "ok"}
    sub.submitted_at = datetime.now(timezone.utc)
    sub.created_at = datetime.now(timezone.utc)
    sub.updated_at = datetime.now(timezone.utc)
    return sub


def _make_reputation_snapshot(agent_id=None, metrics=None):
    snap = MagicMock()
    snap.id = uuid.uuid4()
    snap.agent_id = agent_id or uuid.uuid4()
    snap.metrics = metrics or {
        "total_submissions": 5,
        "passed": 4,
        "failed": 1,
        "pass_rate": 0.8,
        "quality_score": 80.0,
    }
    snap.snapshot_at = datetime.now(timezone.utc)
    snap.created_at = datetime.now(timezone.utc)
    snap.updated_at = datetime.now(timezone.utc)
    return snap


# ---------------------------------------------------------------------------
# TaskService
# ---------------------------------------------------------------------------

class TestTaskService:
    def _build(self):
        task_repo = AsyncMock()
        submission_repo = AsyncMock()
        svc = TaskService(task_repo, submission_repo)
        return svc, task_repo, submission_repo

    @pytest.mark.asyncio
    async def test_create_task(self):
        svc, task_repo, _ = self._build()
        created = _make_task()
        task_repo.create.return_value = created

        data = TaskCreate(
            task_spec={"type": "coding"},
            publisher_id=uuid.uuid4(),
            reward=5.0,
        )
        result = await svc.create_task(data)

        assert result == created
        task_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_deadline(self):
        svc, task_repo, _ = self._build()
        task_repo.create.return_value = _make_task()

        data = TaskCreate(
            task_spec={"type": "coding"},
            publisher_id=uuid.uuid4(),
            reward=1.0,
            deadline_seconds=3600,
        )
        await svc.create_task(data)

        call_kwargs = task_repo.create.call_args.kwargs
        assert call_kwargs["deadline_at"] is not None

    def test_deadline_seconds_rejects_negative(self):
        with pytest.raises(Exception):
            TaskCreate(
                task_spec={"type": "coding"},
                publisher_id=uuid.uuid4(),
                reward=1.0,
                deadline_seconds=-1,
            )

    def test_deadline_seconds_rejects_zero(self):
        with pytest.raises(Exception):
            TaskCreate(
                task_spec={"type": "coding"},
                publisher_id=uuid.uuid4(),
                reward=1.0,
                deadline_seconds=0,
            )

    @pytest.mark.asyncio
    async def test_claim_task_success(self):
        svc, task_repo, _ = self._build()
        task = _make_task(status="open")
        task_repo.get_for_update.return_value = task
        claimed = _make_task(status="claimed")
        task_repo.update_status.return_value = claimed

        agent_id = uuid.uuid4()
        result = await svc.claim_task(task.id, agent_id)

        assert result == claimed
        task_repo.update_status.assert_called_once()
        call_args = task_repo.update_status.call_args
        assert call_args.args == (task.id, "claimed")
        assert call_args.kwargs["claimed_by"] == agent_id
        assert call_args.kwargs["claimed_at"] is not None

    @pytest.mark.asyncio
    async def test_claim_task_not_found(self):
        svc, task_repo, _ = self._build()
        task_repo.get_for_update.return_value = None

        with pytest.raises(ValueError, match="Task not found"):
            await svc.claim_task(uuid.uuid4(), uuid.uuid4())

    @pytest.mark.asyncio
    async def test_claim_task_not_open(self):
        svc, task_repo, _ = self._build()
        task = _make_task(status="claimed")
        task_repo.get_for_update.return_value = task

        with pytest.raises(InvalidTransitionError, match="claimed -> claimed"):
            await svc.claim_task(task.id, uuid.uuid4())

    @pytest.mark.asyncio
    async def test_get_available_tasks(self):
        svc, task_repo, _ = self._build()
        tasks = [_make_task() for _ in range(3)]
        task_repo.list_available.return_value = tasks

        result = await svc.get_available_tasks(limit=10)

        assert len(result) == 3
        task_repo.list_available.assert_called_once_with(limit=10)

    @pytest.mark.asyncio
    async def test_submit_task_success(self):
        svc, task_repo, submission_repo = self._build()
        agent_id = uuid.uuid4()
        task = _make_task(status="claimed", claimed_by=agent_id)
        task_repo.get.return_value = task

        sub = _make_submission(task_id=task.id, agent_id=agent_id)
        submission_repo.create.return_value = sub

        data = SubmissionCreate(
            task_id=task.id,
            agent_id=agent_id,
            output_data={"result": "ok"},
        )
        result = await svc.submit_task(data)

        assert result == sub
        task_repo.update_status.assert_called_once()
        call_args = task_repo.update_status.call_args
        assert call_args.args == (task.id, "submitted")
        assert call_args.kwargs["submitted_at"] is not None

    @pytest.mark.asyncio
    async def test_submit_task_not_found(self):
        svc, task_repo, _ = self._build()
        task_repo.get.return_value = None

        data = SubmissionCreate(
            task_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            output_data={"result": "ok"},
        )
        with pytest.raises(ValueError, match="Task not found"):
            await svc.submit_task(data)

    @pytest.mark.asyncio
    async def test_submit_task_not_claimed(self):
        svc, task_repo, _ = self._build()
        task = _make_task(status="open")
        task_repo.get.return_value = task

        data = SubmissionCreate(
            task_id=task.id,
            agent_id=uuid.uuid4(),
            output_data={"result": "ok"},
        )
        with pytest.raises(InvalidTransitionError, match="open -> submitted"):
            await svc.submit_task(data)

    @pytest.mark.asyncio
    async def test_submit_task_wrong_agent(self):
        svc, task_repo, _ = self._build()
        task = _make_task(status="claimed", claimed_by=uuid.uuid4())
        task_repo.get.return_value = task

        data = SubmissionCreate(
            task_id=task.id,
            agent_id=uuid.uuid4(),  # different agent
            output_data={"result": "ok"},
        )
        with pytest.raises(ValueError, match="did not claim"):
            await svc.submit_task(data)


# ---------------------------------------------------------------------------
# ValidationService
# ---------------------------------------------------------------------------

class TestValidationService:
    def _make_sub_task(self, output_data, output_schema, validation_method="schema+rule"):
        sub = MagicMock()
        sub.id = uuid.uuid4()
        sub.output_data = output_data
        task = MagicMock()
        task.task_spec = {
            "output_schema": output_schema,
            "validation_method": validation_method,
            "input_data": {},
        }
        return sub, task

    @pytest.mark.asyncio
    async def test_valid_submission(self):
        svc = ValidationService()
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }
        sub, task = self._make_sub_task({"name": "Alice"}, schema)
        result = await svc.validate_submission(sub, task)
        assert result.passed is True
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_schema_validation_fails(self):
        svc = ValidationService()
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }
        sub, task = self._make_sub_task({"name": 123}, schema)
        result = await svc.validate_submission(sub, task)
        assert result.passed is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_rule_validation_fails_empty_value(self):
        svc = ValidationService()
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        }
        sub, task = self._make_sub_task({"name": ""}, schema)
        result = await svc.validate_submission(sub, task)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_missing_required_field(self):
        svc = ValidationService()
        schema = {
            "type": "object",
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
        sub, task = self._make_sub_task({"name": "Alice"}, schema)
        result = await svc.validate_submission(sub, task)
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_schema_fails_short_circuits(self):
        """When schema validation fails, rule validation is skipped."""
        svc = ValidationService()
        schema = {
            "type": "object",
            "required": ["x"],
            "properties": {"x": {"type": "integer"}},
        }
        sub, task = self._make_sub_task({"x": "not_int"}, schema)
        result = await svc.validate_submission(sub, task)
        assert result.passed is False
        # Errors should only be from schema validator
        assert any("integer" in e for e in result.errors)


# ---------------------------------------------------------------------------
# ReputationService
# ---------------------------------------------------------------------------

class TestReputationService:
    def _build(self):
        repo = AsyncMock()
        svc = ReputationService(repo)
        return svc, repo

    @pytest.mark.asyncio
    async def test_first_submission_pass(self):
        svc, repo = self._build()
        repo.get_latest.return_value = None
        repo.create_snapshot.return_value = _make_reputation_snapshot()

        vr = ValidationResult(passed=True, score=1.0, validator_type=ValidatorType.SCHEMA, details="ok")
        await svc.update_reputation(uuid.uuid4(), vr)

        call_kwargs = repo.create_snapshot.call_args.kwargs
        assert call_kwargs["metrics"]["total_submissions"] == 1
        assert call_kwargs["metrics"]["passed"] == 1
        assert call_kwargs["metrics"]["failed"] == 0
        assert call_kwargs["metrics"]["pass_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_first_submission_fail(self):
        svc, repo = self._build()
        repo.get_latest.return_value = None
        repo.create_snapshot.return_value = _make_reputation_snapshot()

        vr = ValidationResult(passed=False, score=0.0, validator_type=ValidatorType.SCHEMA, details="bad")
        await svc.update_reputation(uuid.uuid4(), vr)

        call_kwargs = repo.create_snapshot.call_args.kwargs
        assert call_kwargs["metrics"]["total_submissions"] == 1
        assert call_kwargs["metrics"]["passed"] == 0
        assert call_kwargs["metrics"]["failed"] == 1
        assert call_kwargs["metrics"]["pass_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_incremental_update(self):
        svc, repo = self._build()
        existing = _make_reputation_snapshot(
            metrics={
                "total_submissions": 10,
                "passed": 8,
                "failed": 2,
                "pass_rate": 0.8,
                "quality_score": 80.0,
            }
        )
        repo.get_latest.return_value = existing
        repo.create_snapshot.return_value = _make_reputation_snapshot()

        vr = ValidationResult(passed=True, score=1.0, validator_type=ValidatorType.SCHEMA, details="ok")
        await svc.update_reputation(uuid.uuid4(), vr)

        call_kwargs = repo.create_snapshot.call_args.kwargs
        metrics = call_kwargs["metrics"]
        assert metrics["total_submissions"] == 11
        assert metrics["passed"] == 9
        assert metrics["failed"] == 2
        assert metrics["pass_rate"] == round(9 / 11, 4)

    @pytest.mark.asyncio
    async def test_partial_metrics_dict(self):
        """prev metrics with missing keys should not raise KeyError."""
        svc, repo = self._build()
        # Simulate a snapshot with only some keys present
        existing = _make_reputation_snapshot(metrics={"total_submissions": 3})
        repo.get_latest.return_value = existing
        repo.create_snapshot.return_value = _make_reputation_snapshot()

        vr = ValidationResult(passed=True, score=1.0, validator_type=ValidatorType.SCHEMA, details="ok")
        await svc.update_reputation(uuid.uuid4(), vr)

        call_kwargs = repo.create_snapshot.call_args.kwargs
        metrics = call_kwargs["metrics"]
        assert metrics["total_submissions"] == 4
        assert metrics["passed"] == 1
        assert metrics["failed"] == 0

    @pytest.mark.asyncio
    async def test_empty_metrics_dict(self):
        """prev metrics as empty dict should not raise KeyError."""
        svc, repo = self._build()
        existing = _make_reputation_snapshot()
        existing.metrics = {}  # override after creation to bypass falsy check
        repo.get_latest.return_value = existing
        repo.create_snapshot.return_value = _make_reputation_snapshot()

        vr = ValidationResult(passed=False, score=0.0, validator_type=ValidatorType.SCHEMA, details="bad")
        await svc.update_reputation(uuid.uuid4(), vr)

        call_kwargs = repo.create_snapshot.call_args.kwargs
        metrics = call_kwargs["metrics"]
        assert metrics["total_submissions"] == 1
        assert metrics["passed"] == 0
        assert metrics["failed"] == 1


# ---------------------------------------------------------------------------
# AgentRepository.get_quota_profile
# ---------------------------------------------------------------------------

class TestGetQuotaProfile:
    @pytest.mark.asyncio
    async def test_full_quota_profile(self):
        from agentrelay.repositories.agent_repo import AgentRepository

        session = AsyncMock()
        repo = AgentRepository(session)
        agent = MagicMock()
        agent.quota_profile = {
            "provider": "anthropic",
            "model": "haiku",
            "executor_type": "free_tier",
            "plan_type": "basic",
            "daily_task_budget": 50,
            "safe_token_cap": 8000,
        }
        session.get.return_value = agent

        profile = await repo.get_quota_profile(uuid.uuid4())
        assert profile.provider == "anthropic"
        assert profile.safe_token_cap == 8000
        assert profile.daily_task_budget == 50

    @pytest.mark.asyncio
    async def test_partial_quota_profile_defaults(self):
        from agentrelay.repositories.agent_repo import AgentRepository

        session = AsyncMock()
        repo = AgentRepository(session)
        agent = MagicMock()
        agent.quota_profile = {"safe_token_cap": 1000}
        session.get.return_value = agent

        profile = await repo.get_quota_profile(uuid.uuid4())
        assert profile.provider == "unknown"
        assert profile.model == "unknown"
        assert profile.safe_token_cap == 1000
        assert profile.daily_task_budget == 0

    @pytest.mark.asyncio
    async def test_empty_quota_profile(self):
        from agentrelay.repositories.agent_repo import AgentRepository

        session = AsyncMock()
        repo = AgentRepository(session)
        agent = MagicMock()
        agent.quota_profile = {}
        session.get.return_value = agent

        profile = await repo.get_quota_profile(uuid.uuid4())
        assert profile.safe_token_cap == 0

    @pytest.mark.asyncio
    async def test_none_agent(self):
        from agentrelay.repositories.agent_repo import AgentRepository

        session = AsyncMock()
        repo = AgentRepository(session)
        session.get.return_value = None

        profile = await repo.get_quota_profile(uuid.uuid4())
        assert profile is None


# ---------------------------------------------------------------------------
# QuotaService
# ---------------------------------------------------------------------------

class TestQuotaService:
    def test_within_budget(self):
        svc = QuotaService()
        profile = QuotaProfile(
            provider="anthropic",
            model="haiku",
            executor_type="free_tier",
            plan_type="basic",
            daily_task_budget=100,
            safe_token_cap=10000,
        )
        assert svc.check_quota(profile, 5000) is True

    def test_over_budget(self):
        svc = QuotaService()
        profile = QuotaProfile(
            provider="anthropic",
            model="haiku",
            executor_type="free_tier",
            plan_type="basic",
            daily_task_budget=100,
            safe_token_cap=10000,
        )
        assert svc.check_quota(profile, 15000) is False

    def test_exact_cap(self):
        svc = QuotaService()
        profile = QuotaProfile(
            provider="anthropic",
            model="haiku",
            executor_type="free_tier",
            plan_type="basic",
            daily_task_budget=100,
            safe_token_cap=10000,
        )
        assert svc.check_quota(profile, 10000) is True

    def test_zero_tokens(self):
        svc = QuotaService()
        profile = QuotaProfile(
            provider="anthropic",
            model="haiku",
            executor_type="free_tier",
            plan_type="basic",
            daily_task_budget=100,
            safe_token_cap=10000,
        )
        assert svc.check_quota(profile, 0) is True

    def test_negative_tokens(self):
        svc = QuotaService()
        profile = QuotaProfile(
            provider="anthropic",
            model="haiku",
            executor_type="free_tier",
            plan_type="basic",
            daily_task_budget=100,
            safe_token_cap=10000,
        )
        assert svc.check_quota(profile, -100) is False
