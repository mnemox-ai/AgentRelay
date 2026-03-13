"""Tests for reputation auto-updates — pass raises scores, fail lowers them."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentrelay.domain.validation_result import ValidationResult, ValidatorType
from agentrelay.services.reputation_service import ReputationService


def _make_snapshot(metrics=None, agent_id=None):
    snap = MagicMock()
    snap.id = uuid.uuid4()
    snap.agent_id = agent_id or uuid.uuid4()
    snap.metrics = metrics or {
        "total_submissions": 0,
        "passed": 0,
        "failed": 0,
        "pass_rate": 0.0,
        "quality_score": 0.0,
        "rework_rate": 0.0,
    }
    snap.snapshot_at = datetime.now(timezone.utc)
    snap.created_at = datetime.now(timezone.utc)
    snap.updated_at = datetime.now(timezone.utc)
    return snap


class TestReputationOnPass:
    def _build(self):
        repo = AsyncMock()
        svc = ReputationService(repo)
        return svc, repo

    @pytest.mark.asyncio
    async def test_pass_increases_pass_rate(self):
        svc, repo = self._build()
        repo.get_latest.return_value = _make_snapshot(
            metrics={
                "total_submissions": 4,
                "passed": 2,
                "failed": 2,
                "pass_rate": 0.5,
                "quality_score": 50.0,
                "rework_rate": 0.5,
            }
        )
        repo.create_snapshot.return_value = _make_snapshot()

        vr = ValidationResult(
            passed=True, score=0.9, validator_type=ValidatorType.SCHEMA, details="ok"
        )
        await svc.update_reputation(uuid.uuid4(), vr)

        metrics = repo.create_snapshot.call_args.kwargs["metrics"]
        assert metrics["passed"] == 3
        assert metrics["total_submissions"] == 5
        assert metrics["pass_rate"] == 0.6  # 3/5
        assert metrics["rework_rate"] == 0.4  # 2/5

    @pytest.mark.asyncio
    async def test_pass_quality_score_uses_weighted_average(self):
        svc, repo = self._build()
        repo.get_latest.return_value = _make_snapshot(
            metrics={
                "total_submissions": 2,
                "passed": 2,
                "failed": 0,
                "pass_rate": 1.0,
                "quality_score": 80.0,
                "rework_rate": 0.0,
            }
        )
        repo.create_snapshot.return_value = _make_snapshot()

        vr = ValidationResult(
            passed=True, score=1.0, validator_type=ValidatorType.SCHEMA, details="ok"
        )
        await svc.update_reputation(uuid.uuid4(), vr)

        metrics = repo.create_snapshot.call_args.kwargs["metrics"]
        # (80*2 + 100*1) / 3 = 260/3 ≈ 86.67
        assert metrics["quality_score"] == round((80.0 * 2 + 100.0) / 3, 2)

    @pytest.mark.asyncio
    async def test_first_pass_quality_equals_score(self):
        svc, repo = self._build()
        repo.get_latest.return_value = None
        repo.create_snapshot.return_value = _make_snapshot()

        vr = ValidationResult(
            passed=True, score=0.85, validator_type=ValidatorType.SCHEMA, details="ok"
        )
        await svc.update_reputation(uuid.uuid4(), vr)

        metrics = repo.create_snapshot.call_args.kwargs["metrics"]
        assert metrics["quality_score"] == 85.0
        assert metrics["rework_rate"] == 0.0


class TestReputationOnFail:
    def _build(self):
        repo = AsyncMock()
        svc = ReputationService(repo)
        return svc, repo

    @pytest.mark.asyncio
    async def test_fail_decreases_pass_rate(self):
        svc, repo = self._build()
        repo.get_latest.return_value = _make_snapshot(
            metrics={
                "total_submissions": 4,
                "passed": 3,
                "failed": 1,
                "pass_rate": 0.75,
                "quality_score": 75.0,
                "rework_rate": 0.25,
            }
        )
        repo.create_snapshot.return_value = _make_snapshot()

        vr = ValidationResult(
            passed=False, score=0.0, validator_type=ValidatorType.SCHEMA, details="bad"
        )
        await svc.update_reputation(uuid.uuid4(), vr)

        metrics = repo.create_snapshot.call_args.kwargs["metrics"]
        assert metrics["passed"] == 3
        assert metrics["failed"] == 2
        assert metrics["total_submissions"] == 5
        assert metrics["pass_rate"] == 0.6  # 3/5
        assert metrics["rework_rate"] == 0.4  # 2/5

    @pytest.mark.asyncio
    async def test_fail_increases_rework_rate(self):
        svc, repo = self._build()
        repo.get_latest.return_value = _make_snapshot(
            metrics={
                "total_submissions": 9,
                "passed": 8,
                "failed": 1,
                "pass_rate": round(8 / 9, 4),
                "quality_score": 90.0,
                "rework_rate": round(1 / 9, 4),
            }
        )
        repo.create_snapshot.return_value = _make_snapshot()

        vr = ValidationResult(
            passed=False, score=0.2, validator_type=ValidatorType.RULE, details="fail"
        )
        await svc.update_reputation(uuid.uuid4(), vr)

        metrics = repo.create_snapshot.call_args.kwargs["metrics"]
        assert metrics["rework_rate"] == 0.2  # 2/10

    @pytest.mark.asyncio
    async def test_fail_lowers_quality_score(self):
        svc, repo = self._build()
        repo.get_latest.return_value = _make_snapshot(
            metrics={
                "total_submissions": 1,
                "passed": 1,
                "failed": 0,
                "pass_rate": 1.0,
                "quality_score": 100.0,
                "rework_rate": 0.0,
            }
        )
        repo.create_snapshot.return_value = _make_snapshot()

        vr = ValidationResult(
            passed=False, score=0.0, validator_type=ValidatorType.SCHEMA, details="bad"
        )
        await svc.update_reputation(uuid.uuid4(), vr)

        metrics = repo.create_snapshot.call_args.kwargs["metrics"]
        # (100*1 + 0*1) / 2 = 50.0
        assert metrics["quality_score"] == 50.0

    @pytest.mark.asyncio
    async def test_first_fail(self):
        svc, repo = self._build()
        repo.get_latest.return_value = None
        repo.create_snapshot.return_value = _make_snapshot()

        vr = ValidationResult(
            passed=False, score=0.0, validator_type=ValidatorType.SCHEMA, details="bad"
        )
        await svc.update_reputation(uuid.uuid4(), vr)

        metrics = repo.create_snapshot.call_args.kwargs["metrics"]
        assert metrics["pass_rate"] == 0.0
        assert metrics["rework_rate"] == 1.0
        assert metrics["quality_score"] == 0.0
