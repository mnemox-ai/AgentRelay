"""End-to-end integration test — full task lifecycle.

Covers the complete flow:
  register agent → create task → list available → claim → submit
  → validation → completed status → ledger reward → reputation update
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from agentrelay.models.ledger import LedgerEntry
from agentrelay.models.reputation import ReputationSnapshot
from agentrelay.models.validation_run import ValidationRun


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


# ---------------------------------------------------------------------------
# Full lifecycle integration test
# ---------------------------------------------------------------------------

class TestFullTaskLifecycle:
    """Step 1-9: register → create → list → claim → submit → verify everything."""

    @pytest.mark.asyncio
    async def test_complete_flow(self, client, db_session):
        # ------------------------------------------------------------------
        # Step 1: Register publisher and worker agents
        # ------------------------------------------------------------------
        publisher = await _register_agent(client, "int-publisher")
        worker = await _register_agent(
            client, "int-worker", quota_profile={"safe_token_cap": 50000}
        )

        assert publisher["api_key"]
        assert worker["api_key"]

        # ------------------------------------------------------------------
        # Step 2: Create a research_extraction task with output_schema
        # ------------------------------------------------------------------
        task_spec = {
            "type": "research_extraction",
            "description": "Extract key metrics from the report",
            "input_data": {"url": "https://example.com/report"},
            "output_schema": {
                "type": "object",
                "required": ["title", "metrics"],
                "properties": {
                    "title": {"type": "string"},
                    "metrics": {"type": "array"},
                },
            },
            "validation_method": "schema+rule",
            "token_estimate": 2000,
        }

        create_resp = await client.post(
            "/tasks",
            json={
                "task_spec": task_spec,
                "publisher_id": publisher["id"],
                "reward": 25.0,
                "deadline_seconds": 3600,
            },
            headers=_auth(publisher["api_key"]),
        )
        assert create_resp.status_code == 201
        task = create_resp.json()
        task_id = task["id"]
        assert task["status"] == "open"
        assert task["reward"] == 25.0
        assert task["deadline_at"] is not None

        # ------------------------------------------------------------------
        # Step 3: GET /tasks/available — confirm the task is visible
        # ------------------------------------------------------------------
        avail_resp = await client.get("/tasks/available")
        assert avail_resp.status_code == 200
        available_ids = [t["id"] for t in avail_resp.json()]
        assert task_id in available_ids

        # ------------------------------------------------------------------
        # Step 4: POST /tasks/{id}/claim — worker claims the task
        # ------------------------------------------------------------------
        claim_resp = await client.post(
            f"/tasks/{task_id}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )
        assert claim_resp.status_code == 200
        claimed = claim_resp.json()
        assert claimed["status"] == "claimed"
        assert claimed["claimed_by"] == worker["id"]

        # Task should no longer appear in available list
        avail_resp2 = await client.get("/tasks/available")
        available_ids2 = [t["id"] for t in avail_resp2.json()]
        assert task_id not in available_ids2

        # ------------------------------------------------------------------
        # Step 5: POST /tasks/{id}/submit — worker submits valid output
        # ------------------------------------------------------------------
        output_data = {
            "title": "Q4 Earnings Report",
            "metrics": [
                {"name": "revenue", "value": 1000000},
                {"name": "growth", "value": 15.3},
            ],
        }

        submit_resp = await client.post(
            f"/tasks/{task_id}/submit",
            json={
                "task_id": task_id,
                "agent_id": worker["id"],
                "output_data": output_data,
            },
            headers=_auth(worker["api_key"]),
        )
        assert submit_resp.status_code == 200
        submission = submit_resp.json()
        submission_id = submission["id"]
        assert submission["agent_id"] == worker["id"]
        assert submission["output_data"] == output_data

        # ------------------------------------------------------------------
        # Step 6: Verify validation_runs exist
        # ------------------------------------------------------------------
        val_resp = await client.get(f"/submissions/{submission_id}/validation")
        assert val_resp.status_code == 200
        validation_runs = val_resp.json()
        assert len(validation_runs) >= 1  # at least schema validator ran

        # Verify we have both schema and rule validation runs
        validator_types = {run["validator_type"] for run in validation_runs}
        assert "schema" in validator_types
        assert "rule" in validator_types

        # All validators should have passed
        for run in validation_runs:
            assert run["passed"] is True
            assert run["score"] > 0

        # ------------------------------------------------------------------
        # Step 7: Verify task status = completed
        # ------------------------------------------------------------------
        task_resp = await client.get(f"/tasks/{task_id}")
        assert task_resp.status_code == 200
        assert task_resp.json()["status"] == "completed"

        # ------------------------------------------------------------------
        # Step 8: Verify ledger has reward entry
        # ------------------------------------------------------------------
        worker_uuid = uuid.UUID(worker["id"])
        task_uuid = uuid.UUID(task_id)

        ledger_stmt = select(LedgerEntry).where(
            LedgerEntry.agent_id == worker_uuid,
            LedgerEntry.task_id == task_uuid,
        )
        result = await db_session.execute(ledger_stmt)
        ledger_entries = list(result.scalars().all())

        assert len(ledger_entries) == 1
        entry = ledger_entries[0]
        assert entry.entry_type == "reward"
        assert entry.amount == 25.0

        # ------------------------------------------------------------------
        # Step 9: Verify reputation has been updated
        # ------------------------------------------------------------------
        rep_stmt = (
            select(ReputationSnapshot)
            .where(ReputationSnapshot.agent_id == worker_uuid)
            .order_by(ReputationSnapshot.created_at.desc())
        )
        result = await db_session.execute(rep_stmt)
        snapshots = list(result.scalars().all())

        assert len(snapshots) >= 1
        latest = snapshots[0]
        assert latest.metrics["total_submissions"] >= 1
        assert latest.metrics["passed"] >= 1
        assert latest.metrics["pass_rate"] > 0


class TestFailedValidationFlow:
    """Submit output that fails schema validation — verify failed status + penalty."""

    @pytest.mark.asyncio
    async def test_failed_validation(self, client, db_session):
        publisher = await _register_agent(client, "fail-publisher")
        worker = await _register_agent(client, "fail-worker")

        # Create task with strict output_schema
        task_spec = {
            "type": "research_extraction",
            "output_schema": {
                "type": "object",
                "required": ["summary", "score"],
                "properties": {
                    "summary": {"type": "string"},
                    "score": {"type": "integer"},
                },
            },
            "validation_method": "schema+rule",
        }

        create_resp = await client.post(
            "/tasks",
            json={
                "task_spec": task_spec,
                "publisher_id": publisher["id"],
                "reward": 10.0,
            },
            headers=_auth(publisher["api_key"]),
        )
        task = create_resp.json()
        task_id = task["id"]

        # Claim
        await client.post(
            f"/tasks/{task_id}/claim",
            json={"agent_id": worker["id"]},
            headers=_auth(worker["api_key"]),
        )

        # Submit with wrong types (score should be integer, not string)
        submit_resp = await client.post(
            f"/tasks/{task_id}/submit",
            json={
                "task_id": task_id,
                "agent_id": worker["id"],
                "output_data": {"summary": "test", "score": "not-a-number"},
            },
            headers=_auth(worker["api_key"]),
        )
        assert submit_resp.status_code == 200  # submission accepted, but validation fails

        # Task should be failed
        task_resp = await client.get(f"/tasks/{task_id}")
        assert task_resp.json()["status"] == "failed"

        # Ledger should have penalty
        worker_uuid = uuid.UUID(worker["id"])
        task_uuid = uuid.UUID(task_id)

        ledger_stmt = select(LedgerEntry).where(
            LedgerEntry.agent_id == worker_uuid,
            LedgerEntry.task_id == task_uuid,
        )
        result = await db_session.execute(ledger_stmt)
        entries = list(result.scalars().all())

        assert len(entries) == 1
        assert entries[0].entry_type == "penalty"
        assert entries[0].amount < 0  # penalties are negative
