"""Reputation service — update agent reputation based on validation results."""

from __future__ import annotations

import uuid

from agentrelay.repositories.reputation_repo import ReputationRepository
from agentrelay.validation.base import ValidationResult


class ReputationService:
    def __init__(self, reputation_repo: ReputationRepository) -> None:
        self.reputation_repo = reputation_repo

    async def update_reputation(
        self,
        agent_id: uuid.UUID,
        validation_result: ValidationResult,
    ):
        latest = await self.reputation_repo.get_latest(agent_id)

        if latest is not None:
            prev = latest.metrics
        else:
            prev = {
                "total_submissions": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "quality_score": 0.0,
            }

        total = prev["total_submissions"] + 1
        passed = prev["passed"] + (1 if validation_result.valid else 0)
        failed = prev["failed"] + (0 if validation_result.valid else 1)
        pass_rate = passed / total if total > 0 else 0.0
        quality_score = pass_rate * 100.0

        metrics = {
            "total_submissions": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 4),
            "quality_score": round(quality_score, 2),
        }

        return await self.reputation_repo.create_snapshot(
            agent_id=agent_id,
            metrics=metrics,
        )
