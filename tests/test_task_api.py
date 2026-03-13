"""Tests for task API routes."""

from __future__ import annotations

import uuid

import pytest


async def _create_agent(client, name="worker") -> str:
    resp = await client.post("/agents", json={"name": name})
    return resp.json()["id"]


async def _create_task(client, publisher_id: str) -> dict:
    resp = await client.post(
        "/tasks",
        json={
            "task_spec": {"type": "coding", "description": "write tests"},
            "publisher_id": publisher_id,
            "reward": 5.0,
        },
    )
    return resp.json()


class TestCreateTask:
    @pytest.mark.asyncio
    async def test_create_success(self, client):
        pub_id = await _create_agent(client, "publisher")
        resp = await client.post(
            "/tasks",
            json={
                "task_spec": {"type": "coding"},
                "publisher_id": pub_id,
                "reward": 10.0,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "open"
        assert data["reward"] == 10.0
        assert data["task_spec"] == {"type": "coding"}

    @pytest.mark.asyncio
    async def test_create_with_deadline(self, client):
        pub_id = await _create_agent(client, "pub-dl")
        resp = await client.post(
            "/tasks",
            json={
                "task_spec": {"type": "research"},
                "publisher_id": pub_id,
                "deadline_seconds": 3600,
            },
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
        pub_id = await _create_agent(client, "pub-list")
        await _create_task(client, pub_id)
        await _create_task(client, pub_id)

        resp = await client.get("/tasks/available")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestClaimTask:
    @pytest.mark.asyncio
    async def test_claim_success(self, client):
        pub_id = await _create_agent(client, "pub-claim")
        worker_id = await _create_agent(client, "worker-claim")
        task = await _create_task(client, pub_id)

        resp = await client.post(
            f"/tasks/{task['id']}/claim",
            json={"agent_id": worker_id},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "claimed"
        assert resp.json()["claimed_by"] == worker_id

    @pytest.mark.asyncio
    async def test_claim_already_claimed(self, client):
        pub_id = await _create_agent(client, "pub-dbl")
        w1 = await _create_agent(client, "w1")
        w2 = await _create_agent(client, "w2")
        task = await _create_task(client, pub_id)

        await client.post(f"/tasks/{task['id']}/claim", json={"agent_id": w1})
        resp = await client.post(f"/tasks/{task['id']}/claim", json={"agent_id": w2})
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_claim_not_found(self, client):
        fake_id = str(uuid.uuid4())
        worker_id = await _create_agent(client, "w-nf")
        resp = await client.post(f"/tasks/{fake_id}/claim", json={"agent_id": worker_id})
        assert resp.status_code == 409


class TestSubmitTask:
    @pytest.mark.asyncio
    async def test_submit_success(self, client):
        pub_id = await _create_agent(client, "pub-sub")
        worker_id = await _create_agent(client, "worker-sub")
        task = await _create_task(client, pub_id)

        await client.post(f"/tasks/{task['id']}/claim", json={"agent_id": worker_id})

        resp = await client.post(
            f"/tasks/{task['id']}/submit",
            json={
                "task_id": task["id"],
                "agent_id": worker_id,
                "output_data": {"result": "done"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["output_data"] == {"result": "done"}
        assert data["agent_id"] == worker_id

    @pytest.mark.asyncio
    async def test_submit_unclaimed_task(self, client):
        pub_id = await _create_agent(client, "pub-uncl")
        worker_id = await _create_agent(client, "worker-uncl")
        task = await _create_task(client, pub_id)

        resp = await client.post(
            f"/tasks/{task['id']}/submit",
            json={
                "task_id": task["id"],
                "agent_id": worker_id,
                "output_data": {"result": "done"},
            },
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_submit_wrong_agent(self, client):
        pub_id = await _create_agent(client, "pub-wa")
        w1 = await _create_agent(client, "claimer")
        w2 = await _create_agent(client, "intruder")
        task = await _create_task(client, pub_id)

        await client.post(f"/tasks/{task['id']}/claim", json={"agent_id": w1})

        resp = await client.post(
            f"/tasks/{task['id']}/submit",
            json={
                "task_id": task["id"],
                "agent_id": w2,
                "output_data": {"result": "stolen"},
            },
        )
        assert resp.status_code == 409
