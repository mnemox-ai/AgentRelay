"""Tests for concurrent claim protection and duplicate submission rejection."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from agentrelay.domain.task_lifecycle import InvalidTransitionError
from agentrelay.schemas.submission import SubmissionCreate
from agentrelay.services.task_service import TaskService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_task(task_id=None, status="open", claimed_by=None):
    task = MagicMock()
    task.id = task_id or uuid.uuid4()
    task.status = status
    task.claimed_by = claimed_by
    return task


def _make_submission(task_id=None, agent_id=None):
    sub = MagicMock()
    sub.id = uuid.uuid4()
    sub.task_id = task_id or uuid.uuid4()
    sub.agent_id = agent_id or uuid.uuid4()
    sub.output_data = {"result": "ok"}
    return sub


# ---------------------------------------------------------------------------
# Concurrent claim tests
# ---------------------------------------------------------------------------

class TestConcurrentClaim:
    """Test that concurrent claims on the same task are rejected."""

    def _build(self):
        task_repo = AsyncMock()
        submission_repo = AsyncMock()
        svc = TaskService(task_repo, submission_repo)
        return svc, task_repo, submission_repo

    @pytest.mark.asyncio
    async def test_second_claim_rejected_after_first_claim(self):
        """Simulate two agents trying to claim the same task.

        After agent1 claims, get_for_update returns status='claimed',
        so agent2's claim should raise ValueError.
        """
        svc, task_repo, _ = self._build()
        task_id = uuid.uuid4()
        agent1 = uuid.uuid4()
        agent2 = uuid.uuid4()

        # First claim: task is open
        open_task = _make_task(task_id=task_id, status="open")
        task_repo.get_for_update.return_value = open_task
        claimed_task = _make_task(task_id=task_id, status="claimed", claimed_by=agent1)
        task_repo.update_status.return_value = claimed_task

        result = await svc.claim_task(task_id, agent1)
        assert result.status == "claimed"

        # Second claim: task is already claimed (get_for_update sees locked row)
        task_repo.get_for_update.return_value = claimed_task

        with pytest.raises(InvalidTransitionError, match="claimed -> claimed"):
            await svc.claim_task(task_id, agent2)

    @pytest.mark.asyncio
    async def test_claim_uses_get_for_update(self):
        """Verify claim_task calls get_for_update (not plain get) for row locking."""
        svc, task_repo, _ = self._build()
        task = _make_task(status="open")
        task_repo.get_for_update.return_value = task
        task_repo.update_status.return_value = _make_task(status="claimed")

        await svc.claim_task(task.id, uuid.uuid4())

        task_repo.get_for_update.assert_called_once_with(task.id)
        task_repo.get.assert_not_called()


# ---------------------------------------------------------------------------
# Duplicate submission tests
# ---------------------------------------------------------------------------

class TestDuplicateSubmission:
    """Test that duplicate submissions (same task_id + agent_id) are rejected."""

    def _build(self):
        task_repo = AsyncMock()
        submission_repo = AsyncMock()
        svc = TaskService(task_repo, submission_repo)
        return svc, task_repo, submission_repo

    @pytest.mark.asyncio
    async def test_duplicate_submission_rejected(self):
        """Second submission by same agent for same task should raise ValueError."""
        svc, task_repo, submission_repo = self._build()
        agent_id = uuid.uuid4()
        task = _make_task(status="claimed", claimed_by=agent_id)
        task_repo.get.return_value = task

        # First submission succeeds
        sub = _make_submission(task_id=task.id, agent_id=agent_id)
        submission_repo.create.return_value = sub

        data = SubmissionCreate(
            task_id=task.id,
            agent_id=agent_id,
            output_data={"result": "done"},
        )
        result = await svc.submit_task(data)
        assert result == sub

        # Second submission: repo raises ValueError
        submission_repo.create.side_effect = ValueError(
            f"Duplicate submission: agent {agent_id} already submitted for task {task.id}"
        )
        # Reset task status to claimed for the second attempt
        task_repo.get.return_value = task

        with pytest.raises(ValueError, match="Duplicate submission"):
            await svc.submit_task(data)


# ---------------------------------------------------------------------------
# API-level duplicate submission test
# ---------------------------------------------------------------------------

class TestDuplicateSubmissionAPI:
    """Integration test: duplicate submission returns 409 via API."""

    @pytest.mark.asyncio
    async def test_duplicate_submit_returns_409(self, client):
        # Setup: create agent, task, claim
        resp = await client.post("/agents", json={"name": "pub-dup"})
        pub_key = resp.json()["api_key"]
        pub_id = resp.json()["id"]
        resp = await client.post("/agents", json={"name": "worker-dup"})
        worker_key = resp.json()["api_key"]
        worker_id = resp.json()["id"]

        resp = await client.post(
            "/tasks",
            json={"task_spec": {"type": "coding"}, "publisher_id": pub_id, "reward": 1.0},
            headers={"X-API-Key": pub_key},
        )
        task = resp.json()

        await client.post(
            f"/tasks/{task['id']}/claim",
            json={"agent_id": worker_id},
            headers={"X-API-Key": worker_key},
        )

        submit_body = {
            "task_id": task["id"],
            "agent_id": worker_id,
            "output_data": {"result": "done"},
        }

        # First submit succeeds
        resp = await client.post(
            f"/tasks/{task['id']}/submit",
            json=submit_body,
            headers={"X-API-Key": worker_key},
        )
        assert resp.status_code == 200

        # Second submit should be 409 (task status is now "submitted", not "claimed")
        resp = await client.post(
            f"/tasks/{task['id']}/submit",
            json=submit_body,
            headers={"X-API-Key": worker_key},
        )
        assert resp.status_code == 409
