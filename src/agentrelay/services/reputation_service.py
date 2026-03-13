"""Reputation service — update agent reputation based on validation results."""

from __future__ import annotations

import uuid

from agentrelay.repositories.reputation_repo import ReputationRepository
from agentrelay.domain.validation_result import ValidationResult


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

        total = prev.get("total_submissions", 0) + 1
        passed = prev.get("passed", 0) + (1 if validation_result.passed else 0)
        failed = prev.get("failed", 0) + (0 if validation_result.passed else 1)
        pass_rate = passed / total if total > 0 else 0.0

        # Quality score: weighted moving average using validation score (0-1 → 0-100)
        prev_quality = prev.get("quality_score", 0.0)
        prev_total = prev.get("total_submissions", 0)
        new_score = validation_result.score * 100.0
        if prev_total > 0:
            quality_score = (prev_quality * prev_total + new_score) / total
        else:
            quality_score = new_score

        # Rework rate: proportion of failed submissions
        rework_rate = failed / total if total > 0 else 0.0

        metrics = {
            "total_submissions": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 4),
            "quality_score": round(quality_score, 2),
            "rework_rate": round(rework_rate, 4),
        }

        return await self.reputation_repo.create_snapshot(
            agent_id=agent_id,
            metrics=metrics,
        )
