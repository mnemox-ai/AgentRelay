"""Quota service — check agent token/task budgets."""

from __future__ import annotations

from agentrelay.domain.quota_profile import QuotaProfile


class QuotaService:
    def check_quota(self, quota_profile: QuotaProfile, token_estimate: int) -> bool:
        if token_estimate < 0:
            return False
        if token_estimate > quota_profile.safe_token_cap:
            return False
        return True
