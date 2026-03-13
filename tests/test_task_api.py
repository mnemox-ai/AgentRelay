"""Tests for task API routes."""

from __future__ import annotations

import uuid

import pytest


async def _create_agent(client, name="worker", quota_profile=None) -> dict:
    """Register an agent and return {"id": ..., "api_key": ...}."""
    payload = {"name": name}
    if quota_profile is not None:
        payload["quota_profile"] = quota_profile
    resp = await client.post("/agents", json=payload)
    data = resp.json()
    return {"id": data["id"], "api_key": data["api_key"]}


def _auth(api_key: str) -> dict:
    return {"X-API-Key": api_key}


async def _create_task(client, publisher: dict, task_spec=None) -> dict:
    spec = task_spec or {"type": "coding", "description": "write tests"}
    resp = await client.post(
        "/tasks",
        json={
            "task_spec": spec,
            "publisher_id": publisher["id"],
            "reward": 5.0,
        },
        headers=_auth(publisher["api_key"]),
    )
    return resp.json()


class TestCreateTask:
    @pytest.mark.asyncio
    async def test_create_success(self, client):
        pub = await _create_agent(client, "publisher")
        resp = await client.post(
            "/tasks",
            json={
                "task_spec": {"type": "coding"},
                "publisher_id": pub["id"],
                "reward": 10.0,
            },
            headers=_auth(pub["api_key"]),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "open"
        assert data["reward"] == 10.0
        assert data["task_spec"] == {"type": "coding"}

    @pytest.mark.asyncio
    async def test_create_with_deadline(self, client):
        pub = await _create_agent(client, "pub-dl")
        resp = await client.post(
            "/tasks",
            json={
                "task_spec": {"type": "research"},
                "publisher_id": pub["id"],
                "deadline_seconds": 3600,
            },
            headers=_auth(pub["api_key"]),
        )
        assert resp.status_code == 201
        assert resp.json()["deadline_at"] is not None


class TestListAvailable:
    @pytest.mark.asyncio
    async def test_empty_list(self, client):
        resp = await client.get("/tasks/available")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_returns_open_tasks(self, client):
        pub = await _create_agent(client, "pub-list")
        await _create_task(client, pub)
        await _create_task(client, pub)

        resp = await client.get("/tasks/available")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestGetTask:
    @pytest.mark.asyncio
    async def test_get_task_success(self, client):
        pub = await _create_agent(client, "pub-get")
        task = await _create_task(client, pub)

        resp = await client.get(f"/tasks/{task['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == task["id"]
        assert data["status"] == "open"
        assert data["publisher_id"] == pub["id"]

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/tasks/{fake_id}")
        assert resp.status_code == 404


class TestClaimTask:
    @pytest.mark.asyncio
    async def test_claim_success(self, client):
        pub = await _create_agent(client, "pub-claim")
        worker = await _create_agent(client, "worker-claim")
        task = await _create_task(client, pub)

        resp = await client.post(
            f"/tasks/{task['id']}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "claimed"
        assert resp.json()["claimed_by"] == worker["id"]

    @pytest.mark.asyncio
    async def test_claim_already_claimed(self, client):
        pub = await _create_agent(client, "pub-dbl")
        w1 = await _create_agent(client, "worker-dbl-1")
        w2 = await _create_agent(client, "worker-dbl-2")
        task = await _create_task(client, pub)

        await client.post(
            f"/tasks/{task['id']}/claim",
            json={"agent_id": w1["id"]},
            headers=_auth(w1["api_key"]),
        )
        resp = await client.post(
            f"/tasks/{task['id']}/claim",
            json={"agent_id": w2["id"]},
            headers=_auth(w2["api_key"]),
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_claim_not_found(self, client):
        fake_id = str(uuid.uuid4())
        worker = await _create_agent(client, "worker-nf")
        resp = await client.post(
            f"/tasks/{fake_id}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert resp.status_code == 409


class TestSubmitTask:
    @pytest.mark.asyncio
    async def test_submit_success(self, client):
        pub = await _create_agent(client, "pub-sub")
        worker = await _create_agent(client, "worker-sub")
        task = await _create_task(client, pub)

        await client.post(
            f"/tasks/{task['id']}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )

        resp = await client.post(
            f"/tasks/{task['id']}/submit",
            json={
                "task_id": task["id"],
                "agent_id": worker["id"],
                "output_data": {"result": "done"},
            },
            headers=_auth(worker["api_key"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["output_data"] == {"result": "done"}
        assert data["agent_id"] == worker["id"]

    @pytest.mark.asyncio
    async def test_submit_unclaimed_task(self, client):
        pub = await _create_agent(client, "pub-uncl")
        worker = await _create_agent(client, "worker-uncl")
        task = await _create_task(client, pub)

        resp = await client.post(
            f"/tasks/{task['id']}/submit",
            json={
                "task_id": task["id"],
                "agent_id": worker["id"],
                "output_data": {"result": "done"},
            },
            headers=_auth(worker["api_key"]),
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_submit_wrong_agent(self, client):
        pub = await _create_agent(client, "pub-wa")
        w1 = await _create_agent(client, "claimer")
        w2 = await _create_agent(client, "intruder")
        task = await _create_task(client, pub)

        await client.post(
            f"/tasks/{task['id']}/claim",
            json={"agent_id": w1["id"]},
            headers=_auth(w1["api_key"]),
        )

        resp = await client.post(
            f"/tasks/{task['id']}/submit",
            json={
                "task_id": task["id"],
                "agent_id": w2["id"],
                "output_data": {"result": "stolen"},
            },
            headers=_auth(w2["api_key"]),
        )
        assert resp.status_code == 409


class TestTokenLimiterOnClaim:
    @pytest.mark.asyncio
    async def test_claim_rejected_when_over_token_budget(self, client):
        """Task with token_estimate > agent's safe_token_cap should be rejected."""
        pub = await _create_agent(client, "pub-token")
        worker = await _create_agent(
            client, "worker-limited", quota_profile={"safe_token_cap": 1000}
        )
        task = await _create_task(
            client, pub, task_spec={"type": "coding", "token_estimate": 5000}
        )

        resp = await client.post(
            f"/tasks/{task['id']}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert resp.status_code == 403
        assert "Token budget exceeded" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_claim_allowed_within_token_budget(self, client):
        """Task with token_estimate <= agent's safe_token_cap should be allowed."""
        pub = await _create_agent(client, "pub-token-ok")
        worker = await _create_agent(
            client, "worker-ok", quota_profile={"safe_token_cap": 10000}
        )
        task = await _create_task(
            client, pub, task_spec={"type": "coding", "token_estimate": 5000}
        )

        resp = await client.post(
            f"/tasks/{task['id']}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "claimed"

    @pytest.mark.asyncio
    async def test_claim_allowed_when_no_token_estimate(self, client):
        """Tasks without token_estimate should not be blocked."""
        pub = await _create_agent(client, "pub-no-est")
        worker = await _create_agent(
            client, "worker-no-est", quota_profile={"safe_token_cap": 1000}
        )
        task = await _create_task(client, pub)

        resp = await client.post(
            f"/tasks/{task['id']}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert resp.status_code == 200
