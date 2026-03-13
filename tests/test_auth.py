"""Tests for API key authentication."""

from __future__ import annotations

import pytest


class TestAuthMiddleware:
    """Authenticated endpoints reject missing/bad keys, accept valid keys."""

    @pytest.mark.asyncio
    async def test_no_key_returns_401(self, client):
        resp = await client.post(
            "/tasks",
            json={"task_spec": {"type": "coding"}, "publisher_id": "00000000-0000-0000-0000-000000000000", "reward": 1.0},
        )
        assert resp.status_code == 401
        assert "Missing" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_bad_key_returns_401(self, client):
        resp = await client.post(
            "/tasks",
            json={"task_spec": {"type": "coding"}, "publisher_id": "00000000-0000-0000-0000-000000000000", "reward": 1.0},
            headers={"X-API-Key": "invalid_key_that_does_not_exist"},
        )
        assert resp.status_code == 401
        assert "Invalid" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_valid_key_returns_200(self, client):
        # Register agent (public endpoint, returns api_key)
        resp = await client.post("/agents", json={"name": "auth-bot"})
        assert resp.status_code == 201
        data = resp.json()
        api_key = data["api_key"]

        # Use the key to create a task (authenticated endpoint)
        resp = await client.post(
            "/tasks",
            json={"task_spec": {"type": "coding"}, "publisher_id": data["id"], "reward": 1.0},
            headers={"X-API-Key": api_key},
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_api_key_only_returned_on_registration(self, client):
        # Register — api_key present
        resp = await client.post("/agents", json={"name": "once-bot"})
        assert resp.status_code == 201
        data = resp.json()
        assert "api_key" in data
        assert len(data["api_key"]) == 64

        # GET the same agent — api_key NOT present
        agent_id = data["id"]
        resp = await client.get(f"/agents/{agent_id}")
        assert resp.status_code == 200
        assert "api_key" not in resp.json()


class TestPublicEndpoints:
    """Public endpoints should NOT require auth."""

    @pytest.mark.asyncio
    async def test_health_no_auth(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_available_tasks_no_auth(self, client):
        resp = await client.get("/tasks/available")
        assert resp.status_code == 200


class TestClaimSubmitAuth:
    """Claim and submit endpoints require auth."""

    @pytest.mark.asyncio
    async def test_claim_no_key_returns_401(self, client):
        resp = await client.post(
            "/tasks/00000000-0000-0000-0000-000000000000/claim",
            json={"agent_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_submit_no_key_returns_401(self, client):
        resp = await client.post(
            "/tasks/00000000-0000-0000-0000-000000000000/submit",
            json={
                "task_id": "00000000-0000-0000-0000-000000000000",
                "agent_id": "00000000-0000-0000-0000-000000000000",
                "output_data": {},
            },
        )
        assert resp.status_code == 401
