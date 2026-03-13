"""Tests for dashboard API endpoints."""

from __future__ import annotations

import uuid

import pytest


# ---------------------------------------------------------------------------
# Helpers
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


async def _create_and_complete_task(client, publisher: dict, worker: dict, reward: float = 10.0):
    """Helper: create task → claim → submit (valid output) → completed."""
    task_spec = {
        "type": "research_extraction",
        "input_data": {"url": "https://example.com"},
        "output_schema": {
            "type": "object",
            "required": ["title"],
            "properties": {"title": {"type": "string"}},
        },
        "validation_method": "schema+rule",
    }
    create_resp = await client.post(
        "/tasks",
        json={"task_spec": task_spec, "publisher_id": publisher["id"], "reward": reward},
        headers=_auth(publisher["api_key"]),
    )
    assert create_resp.status_code == 201
    task = create_resp.json()
    task_id = task["id"]

    await client.post(
        f"/tasks/{task_id}/claim",
        json={"agent_id": worker["id"]},
        headers=_auth(worker["api_key"]),
    )
    await client.post(
        f"/tasks/{task_id}/submit",
        json={
            "task_id": task_id,
            "agent_id": worker["id"],
            "output_data": {"title": "Test Result"},
        },
        headers=_auth(worker["api_key"]),
    )
    return task_id


# ---------------------------------------------------------------------------
# GET /dashboard/stats
# ---------------------------------------------------------------------------

class TestDashboardStats:
    @pytest.mark.asyncio
    async def test_empty_stats(self, client):
        resp = await client.get("/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tasks"] == 0
        assert data["completed_tasks"] == 0
        assert data["active_agents"] == 0
        assert data["total_rewards"] == 0.0

    @pytest.mark.asyncio
    async def test_stats_after_task_completion(self, client):
        publisher = await _register_agent(client, "dash-pub")
        worker = await _register_agent(client, "dash-worker")
        await _create_and_complete_task(client, publisher, worker, reward=25.0)

        resp = await client.get("/dashboard/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tasks"] == 1
        assert data["completed_tasks"] == 1
        assert data["active_agents"] == 2  # publisher + worker
        assert data["total_rewards"] == 25.0


# ---------------------------------------------------------------------------
# GET /dashboard/tasks/recent
# ---------------------------------------------------------------------------

class TestRecentTasks:
    @pytest.mark.asyncio
    async def test_empty(self, client):
        resp = await client.get("/dashboard/tasks/recent")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_returns_tasks_with_agent_and_score(self, client):
        publisher = await _register_agent(client, "recent-pub")
        worker = await _register_agent(client, "recent-worker")
        await _create_and_complete_task(client, publisher, worker)

        resp = await client.get("/dashboard/tasks/recent")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 1
        task = tasks[0]
        assert task["agent_name"] == "recent-worker"
        assert task["status"] == "completed"
        assert task["validation_score"] is not None
        assert task["validation_score"] > 0


# ---------------------------------------------------------------------------
# GET /dashboard/agents/top
# ---------------------------------------------------------------------------

class TestTopAgents:
    @pytest.mark.asyncio
    async def test_empty(self, client):
        resp = await client.get("/dashboard/agents/top")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_returns_agents_ranked(self, client):
        publisher = await _register_agent(client, "top-pub")
        worker = await _register_agent(client, "top-worker")
        await _create_and_complete_task(client, publisher, worker)

        resp = await client.get("/dashboard/agents/top")
        assert resp.status_code == 200
        agents = resp.json()
        assert len(agents) >= 1
        top = agents[0]
        assert top["name"] == "top-worker"
        assert top["quality_score"] > 0
        assert top["total_submissions"] >= 1
        assert top["pass_rate"] > 0


# ---------------------------------------------------------------------------
# GET /dashboard/validation-rate
# ---------------------------------------------------------------------------

class TestValidationRate:
    @pytest.mark.asyncio
    async def test_empty(self, client):
        resp = await client.get("/dashboard/validation-rate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["passed"] == 0
        assert data["total"] == 0
        assert data["rate"] == 0.0

    @pytest.mark.asyncio
    async def test_rate_after_completion(self, client):
        publisher = await _register_agent(client, "rate-pub")
        worker = await _register_agent(client, "rate-worker")
        await _create_and_complete_task(client, publisher, worker)

        resp = await client.get("/dashboard/validation-rate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        assert data["passed"] > 0
        assert data["rate"] > 0


# ---------------------------------------------------------------------------
# GET /dashboard/agents/{id}/ledger
# ---------------------------------------------------------------------------

class TestAgentLedger:
    @pytest.mark.asyncio
    async def test_not_found(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/dashboard/agents/{fake_id}/ledger")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_ledger(self, client):
        agent = await _register_agent(client, "ledger-agent")
        resp = await client.get(f"/dashboard/agents/{agent['id']}/ledger")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_ledger_with_entries(self, client):
        publisher = await _register_agent(client, "ledger-pub")
        worker = await _register_agent(client, "ledger-worker")
        await _create_and_complete_task(client, publisher, worker, reward=15.0)

        resp = await client.get(f"/dashboard/agents/{worker['id']}/ledger")
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) >= 1
        assert entries[0]["entry_type"] == "reward"
        assert entries[0]["amount"] == 15.0


# ---------------------------------------------------------------------------
# GET /dashboard/agents/{id}/reputation
# ---------------------------------------------------------------------------

class TestAgentReputation:
    @pytest.mark.asyncio
    async def test_not_found_agent(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/dashboard/agents/{fake_id}/reputation")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_no_reputation_yet(self, client):
        agent = await _register_agent(client, "rep-no-data")
        resp = await client.get(f"/dashboard/agents/{agent['id']}/reputation")
        assert resp.status_code == 404
        assert "No reputation data" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_reputation_after_task(self, client):
        publisher = await _register_agent(client, "rep-pub")
        worker = await _register_agent(client, "rep-worker")
        await _create_and_complete_task(client, publisher, worker)

        resp = await client.get(f"/dashboard/agents/{worker['id']}/reputation")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == worker["id"]
        assert data["metrics"]["total_submissions"] >= 1
        assert data["metrics"]["passed"] >= 1
