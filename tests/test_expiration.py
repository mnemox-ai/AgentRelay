"""Tests for task expiration service and endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from agentrelay.models.task import Task
from agentrelay.models.reputation import ReputationSnapshot
from agentrelay.models.ledger import LedgerEntry


# ---------------------------------------------------------------------------
# Helpers — reuse patterns from test_task_api.py
# ---------------------------------------------------------------------------

async def _create_agent(client, name="worker", quota_profile=None) -> dict:
    payload = {"name": name}
    if quota_profile is not None:
        payload["quota_profile"] = quota_profile
    resp = await client.post("/agents", json=payload)
    return {"id": resp.json()["id"], "api_key": resp.json()["api_key"]}


def _auth(api_key: str) -> dict:
    return {"X-API-Key": api_key}


async def _create_task_with_deadline(client, publisher, deadline_seconds=3600):
    """Create a task with a specific deadline via the API."""
    resp = await client.post(
        "/tasks",
        json={
            "task_spec": {"type": "coding", "description": "expiring task"},
            "publisher_id": publisher["id"],
            "reward": 10.0,
            "deadline_seconds": deadline_seconds,
        },
        headers=_auth(publisher["api_key"]),
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# Unit tests — expire_overdue_tasks directly
# ---------------------------------------------------------------------------

class TestExpireOverdueTasks:
    @pytest.mark.asyncio
    async def test_open_task_past_deadline_expires(self, client):
        """An open task whose deadline has passed should be expired."""
        pub = await _create_agent(client, "pub-exp-open")
        task_data = await _create_task_with_deadline(client, pub, deadline_seconds=3600)

        # Manually set deadline to the past via raw SQL through the endpoint DB
        from tests.conftest import TestSessionFactory
        async with TestSessionFactory() as session:
            task = await session.get(Task, uuid.UUID(task_data["id"]))
            task.deadline_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        # Trigger expiration
        resp = await client.post("/tasks/expire", headers=_auth(pub["api_key"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["expired_count"] == 1
        assert data["expired"][0]["task_id"] == task_data["id"]
        assert data["expired"][0]["previous_status"] == "open"
        assert data["expired"][0]["was_claimed"] is False

        # Verify task is now expired
        resp = await client.get(f"/tasks/{task_data['id']}")
        assert resp.json()["status"] == "expired"

    @pytest.mark.asyncio
    async def test_claimed_task_past_deadline_expires_with_penalty(self, client):
        """A claimed task whose deadline has passed should be expired and the agent penalised."""
        pub = await _create_agent(client, "pub-exp-claim")
        worker = await _create_agent(client, "worker-exp-claim")
        task_data = await _create_task_with_deadline(client, pub, deadline_seconds=3600)

        # Claim the task
        resp = await client.post(
            f"/tasks/{task_data['id']}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert resp.status_code == 200

        # Set deadline to past
        from tests.conftest import TestSessionFactory
        async with TestSessionFactory() as session:
            task = await session.get(Task, uuid.UUID(task_data["id"]))
            task.deadline_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        # Trigger expiration
        resp = await client.post("/tasks/expire", headers=_auth(pub["api_key"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["expired_count"] == 1

        expired_entry = data["expired"][0]
        assert expired_entry["task_id"] == task_data["id"]
        assert expired_entry["previous_status"] == "claimed"
        assert expired_entry["was_claimed"] is True
        assert expired_entry["agent_id"] == worker["id"]
        assert expired_entry["penalty"] == 5.0  # 10.0 * 0.5

        # Verify task is now expired
        resp = await client.get(f"/tasks/{task_data['id']}")
        assert resp.json()["status"] == "expired"

        # Verify ledger penalty was recorded
        from tests.conftest import TestSessionFactory
        async with TestSessionFactory() as session:
            stmt = select(LedgerEntry).where(
                LedgerEntry.agent_id == uuid.UUID(worker["id"])
            )
            result = await session.execute(stmt)
            entries = list(result.scalars().all())
            assert len(entries) == 1
            assert entries[0].amount == -5.0
            assert entries[0].entry_type == "penalty"

        # Verify reputation snapshot was created with incomplete count
        async with TestSessionFactory() as session:
            stmt = select(ReputationSnapshot).where(
                ReputationSnapshot.agent_id == uuid.UUID(worker["id"])
            )
            result = await session.execute(stmt)
            snapshots = list(result.scalars().all())
            assert len(snapshots) == 1
            assert snapshots[0].metrics["incomplete"] == 1

    @pytest.mark.asyncio
    async def test_task_not_past_deadline_not_expired(self, client):
        """A task whose deadline is in the future should NOT be expired."""
        pub = await _create_agent(client, "pub-exp-future")
        task_data = await _create_task_with_deadline(client, pub, deadline_seconds=3600)

        # Deadline is 1 hour in the future — should not expire
        resp = await client.post("/tasks/expire", headers=_auth(pub["api_key"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["expired_count"] == 0

        # Task should still be open
        resp = await client.get(f"/tasks/{task_data['id']}")
        assert resp.json()["status"] == "open"

    @pytest.mark.asyncio
    async def test_task_without_deadline_not_expired(self, client):
        """A task without a deadline should never be expired."""
        pub = await _create_agent(client, "pub-exp-nodl")
        resp = await client.post(
            "/tasks",
            json={
                "task_spec": {"type": "coding"},
                "publisher_id": pub["id"],
                "reward": 5.0,
            },
            headers=_auth(pub["api_key"]),
        )
        assert resp.status_code == 201

        resp = await client.post("/tasks/expire", headers=_auth(pub["api_key"]))
        assert resp.status_code == 200
        assert resp.json()["expired_count"] == 0

    @pytest.mark.asyncio
    async def test_already_expired_task_not_touched(self, client):
        """A task already in expired status should not be processed again."""
        pub = await _create_agent(client, "pub-exp-already")
        task_data = await _create_task_with_deadline(client, pub, deadline_seconds=3600)

        # Set deadline to past
        from tests.conftest import TestSessionFactory
        async with TestSessionFactory() as session:
            task = await session.get(Task, uuid.UUID(task_data["id"]))
            task.deadline_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        # First expiration
        resp = await client.post("/tasks/expire", headers=_auth(pub["api_key"]))
        assert resp.json()["expired_count"] == 1

        # Second expiration — should find nothing
        resp = await client.post("/tasks/expire", headers=_auth(pub["api_key"]))
        assert resp.json()["expired_count"] == 0

    @pytest.mark.asyncio
    async def test_multiple_overdue_tasks(self, client):
        """Multiple overdue tasks should all be expired in one call."""
        pub = await _create_agent(client, "pub-exp-multi")
        task1 = await _create_task_with_deadline(client, pub, deadline_seconds=3600)
        task2 = await _create_task_with_deadline(client, pub, deadline_seconds=3600)
        task3 = await _create_task_with_deadline(client, pub, deadline_seconds=3600)

        # Set all deadlines to past
        from tests.conftest import TestSessionFactory
        async with TestSessionFactory() as session:
            for tid in [task1["id"], task2["id"], task3["id"]]:
                task = await session.get(Task, uuid.UUID(tid))
                task.deadline_at = datetime.now(timezone.utc) - timedelta(hours=1)
            await session.commit()

        resp = await client.post("/tasks/expire", headers=_auth(pub["api_key"]))
        assert resp.status_code == 200
        assert resp.json()["expired_count"] == 3
