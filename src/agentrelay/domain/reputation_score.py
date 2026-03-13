"""Reputation score domain objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReputationMetrics:
    completion_rate: float
    pass_rate: float
    avg_latency_seconds: float
    token_efficiency: float
    rework_rate: float
    quality_score: float
