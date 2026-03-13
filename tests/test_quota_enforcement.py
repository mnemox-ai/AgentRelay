"""Tests for quota enforcement on task claim."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentrelay.domain.quota_profile import QuotaProfile
from agentrelay.services.quota_service import QuotaExceededError, QuotaService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(token_estimate: int = 1000):
    task = MagicMock()
    task.id = uuid.uuid4()
    task.task_spec = {"token_estimate": token_estimate}
    return task


def _make_quota_profile(daily_task_budget: int = 10, safe_token_cap: int = 10000):
    return QuotaProfile(
        provider="anthropic",
        model="haiku",
        executor_type="free_tier",
        plan_type="basic",
        daily_task_budget=daily_task_budget,
        safe_token_cap=safe_token_cap,
    )


def _build_quota_service(quota_profile, claimed_today: int = 0):
    task_repo = AsyncMock()
    task_repo.count_claimed_today.return_value = claimed_today
    agent_repo = AsyncMock()
    agent_repo.get_quota_profile.return_value = quota_profile
    svc = QuotaService(task_repo=task_repo, agent_repo=agent_repo)
    return svc


# ---------------------------------------------------------------------------
# Unit tests — QuotaService.check_and_deduct_quota
# ---------------------------------------------------------------------------

class TestCheckAndDeductQuota:
    @pytest.mark.asyncio
    async def test_quota_ok_claim_allowed(self):
        """Budget has room and token estimate is within cap → passes."""
        svc = _build_quota_service(_make_quota_profile(daily_task_budget=10, safe_token_cap=10000), claimed_today=3)
        task = _make_task(token_estimate=5000)
        # Should not raise
        await svc.check_and_deduct_quota(uuid.uuid4(), task)

    @pytest.mark.asyncio
    async def test_daily_budget_exhausted(self):
        """All daily budget used → QuotaExceededError."""
        svc = _build_quota_service(_make_quota_profile(daily_task_budget=5, safe_token_cap=10000), claimed_today=5)
        task = _make_task(token_estimate=1000)
        with pytest.raises(QuotaExceededError, match="Daily task budget exceeded"):
            await svc.check_and_deduct_quota(uuid.uuid4(), task)

    @pytest.mark.asyncio
    async def test_token_cap_exceeded(self):
        """Task token estimate exceeds agent cap → QuotaExceededError."""
        svc = _build_quota_service(_make_quota_profile(daily_task_budget=10, safe_token_cap=1000), claimed_today=0)
        task = _make_task(token_estimate=5000)
        with pytest.raises(QuotaExceededError, match="Token budget exceeded"):
            await svc.check_and_deduct_quota(uuid.uuid4(), task)

    @pytest.mark.asyncio
    async def test_no_quota_profile_allows_claim(self):
        """Agent has no quota profile → claim allowed."""
        svc = _build_quota_service(None, claimed_today=0)
        task = _make_task(token_estimate=5000)
        await svc.check_and_deduct_quota(uuid.uuid4(), task)

    @pytest.mark.asyncio
    async def test_zero_daily_budget_skips_check(self):
        """daily_task_budget=0 means unlimited → no budget check."""
        svc = _build_quota_service(_make_quota_profile(daily_task_budget=0, safe_token_cap=10000), claimed_today=999)
        task = _make_task(token_estimate=1000)
        await svc.check_and_deduct_quota(uuid.uuid4(), task)

    @pytest.mark.asyncio
    async def test_zero_token_estimate_skips_token_check(self):
        """Task with no token_estimate → token check skipped."""
        svc = _build_quota_service(_make_quota_profile(daily_task_budget=10, safe_token_cap=100), claimed_today=0)
        task = _make_task(token_estimate=0)
        await svc.check_and_deduct_quota(uuid.uuid4(), task)


# ---------------------------------------------------------------------------
# Integration tests — claim endpoint with quota enforcement
# ---------------------------------------------------------------------------

async def _register_agent(client, name: str, quota_profile: dict | None = None) -> dict:
    payload: dict = {"name": name}
    if quota_profile is not None:
        payload["quota_profile"] = quota_profile
    resp = await client.post("/agents", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {"id": data["id"], "api_key": data["api_key"]}


def _auth(api_key: str) -> dict:
    return {"X-API-Key": api_key}


async def _create_task(client, publisher, token_estimate: int = 1000) -> str:
    task_spec = {
        "type": "coding",
        "description": "Test task",
        "input_data": {"url": "https://example.com"},
        "output_schema": {"type": "object", "properties": {"result": {"type": "string"}}},
        "validation_method": "schema",
        "token_estimate": token_estimate,
    }
    resp = await client.post(
        "/tasks",
        json={"task_spec": task_spec, "publisher_id": publisher["id"], "reward": 1.0, "deadline_seconds": 3600},
        headers=_auth(publisher["api_key"]),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestClaimEndpointQuota:
    @pytest.mark.asyncio
    async def test_claim_succeeds_within_quota(self, client):
        publisher = await _register_agent(client, f"pub-{uuid.uuid4().hex[:8]}")
        worker = await _register_agent(
            client, f"wrk-{uuid.uuid4().hex[:8]}",
            quota_profile={"daily_task_budget": 10, "safe_token_cap": 50000},
        )
        task_id = await _create_task(client, publisher, token_estimate=2000)
        resp = await client.post(
            f"/tasks/{task_id}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "claimed"

    @pytest.mark.asyncio
    async def test_claim_rejected_daily_budget_exceeded(self, client):
        publisher = await _register_agent(client, f"pub-{uuid.uuid4().hex[:8]}")
        worker = await _register_agent(
            client, f"wrk-{uuid.uuid4().hex[:8]}",
            quota_profile={"daily_task_budget": 1, "safe_token_cap": 50000},
        )
        # Claim first task — uses up the budget
        task1_id = await _create_task(client, publisher, token_estimate=1000)
        resp1 = await client.post(
            f"/tasks/{task1_id}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert resp1.status_code == 200

        # Second claim should be rejected
        task2_id = await _create_task(client, publisher, token_estimate=1000)
        resp2 = await client.post(
            f"/tasks/{task2_id}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert resp2.status_code == 403
        assert "Daily task budget exceeded" in resp2.json()["detail"]

    @pytest.mark.asyncio
    async def test_claim_rejected_token_too_large(self, client):
        publisher = await _register_agent(client, f"pub-{uuid.uuid4().hex[:8]}")
        worker = await _register_agent(
            client, f"wrk-{uuid.uuid4().hex[:8]}",
            quota_profile={"daily_task_budget": 10, "safe_token_cap": 500},
        )
        task_id = await _create_task(client, publisher, token_estimate=5000)
        resp = await client.post(
            f"/tasks/{task_id}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert resp.status_code == 403
        assert "Token budget exceeded" in resp.json()["detail"]
