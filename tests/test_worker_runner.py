"""Tests for WorkerRunner — mock httpx + executor."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agentrelay.worker.executor import ExecutionResult, ExecutionStatus
from agentrelay.worker.runner import WorkerRunner


@pytest.fixture
def runner():
    r = WorkerRunner("http://localhost:8000", agent_name="test-worker", poll_interval=1)
    return r


class TestRegister:
    async def test_register_success(self, runner: WorkerRunner):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "id": "aaaa-bbbb-cccc-dddd",
            "name": "test-worker",
            "api_key": "hexkey123",
        }
        runner.client = AsyncMock()
        runner.client.post = AsyncMock(return_value=mock_resp)

        await runner._register()

        assert runner.agent_id == "aaaa-bbbb-cccc-dddd"
        assert runner.api_key == "hexkey123"

    async def test_register_409_retries(self, runner: WorkerRunner):
        resp_409 = MagicMock()
        resp_409.status_code = 409

        resp_201 = MagicMock()
        resp_201.status_code = 201
        resp_201.json.return_value = {
            "id": "aaaa-1111",
            "name": "test-worker-1234",
            "api_key": "key2",
        }

        runner.client = AsyncMock()
        runner.client.post = AsyncMock(side_effect=[resp_409, resp_201])

        await runner._register()

        assert runner.agent_id == "aaaa-1111"
        assert runner.client.post.call_count == 2


class TestPollTasks:
    async def test_poll_returns_tasks(self, runner: WorkerRunner):
        runner.agent_id = "agent-1"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [{"id": "task-1", "task_spec": {}}]

        runner.client = AsyncMock()
        runner.client.get = AsyncMock(return_value=mock_resp)

        tasks = await runner._poll_tasks()
        assert len(tasks) == 1

    async def test_poll_empty(self, runner: WorkerRunner):
        runner.agent_id = "agent-1"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = []

        runner.client = AsyncMock()
        runner.client.get = AsyncMock(return_value=mock_resp)

        tasks = await runner._poll_tasks()
        assert tasks == []


class TestClaimTask:
    async def test_claim_success(self, runner: WorkerRunner):
        runner.agent_id = "agent-1"
        runner.api_key = "key"
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        runner.client = AsyncMock()
        runner.client.post = AsyncMock(return_value=mock_resp)

        assert await runner._claim_task("task-1") is True

    async def test_claim_conflict(self, runner: WorkerRunner):
        runner.agent_id = "agent-1"
        runner.api_key = "key"
        mock_resp = MagicMock()
        mock_resp.status_code = 409

        runner.client = AsyncMock()
        runner.client.post = AsyncMock(return_value=mock_resp)

        assert await runner._claim_task("task-1") is False


class TestProcessTask:
    async def test_full_cycle_completed(self, runner: WorkerRunner):
        runner.agent_id = "agent-1"
        runner.api_key = "key"

        task = {
            "id": "abcd1234-0000-0000-0000-000000000000",
            "task_spec": {"task_type": "coding", "difficulty": "easy", "input_data": {}},
        }

        # Mock claim
        claim_resp = MagicMock()
        claim_resp.status_code = 200

        # Mock submit
        submit_resp = MagicMock()
        submit_resp.status_code = 200
        submit_resp.json.return_value = {"id": "sub-1"}

        # Mock get task (status check)
        get_resp = MagicMock()
        get_resp.status_code = 200
        get_resp.json.return_value = {"status": "completed"}

        runner.client = AsyncMock()
        runner.client.post = AsyncMock(side_effect=[claim_resp, submit_resp])
        runner.client.get = AsyncMock(return_value=get_resp)

        # Mock executor
        runner.executor = AsyncMock()
        runner.executor.execute = AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output='{"result": 42}',
                output_data={"result": 42},
                return_code=0,
                duration_seconds=1.5,
            )
        )

        await runner._process_task(task)

        assert runner.stats["completed"] == 1
        assert runner.stats["reputation"] == 1050

    async def test_full_cycle_failed_validation(self, runner: WorkerRunner):
        runner.agent_id = "agent-1"
        runner.api_key = "key"

        task = {
            "id": "abcd1234-0000-0000-0000-000000000000",
            "task_spec": {"task_type": "coding"},
        }

        claim_resp = MagicMock()
        claim_resp.status_code = 200

        submit_resp = MagicMock()
        submit_resp.status_code = 200
        submit_resp.json.return_value = {"id": "sub-1"}

        get_resp = MagicMock()
        get_resp.status_code = 200
        get_resp.json.return_value = {"status": "failed"}

        runner.client = AsyncMock()
        runner.client.post = AsyncMock(side_effect=[claim_resp, submit_resp])
        runner.client.get = AsyncMock(return_value=get_resp)

        runner.executor = AsyncMock()
        runner.executor.execute = AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output="{}",
                output_data={},
                return_code=0,
                duration_seconds=0.5,
            )
        )

        await runner._process_task(task)

        assert runner.stats["failed"] == 1
        assert runner.stats["reputation"] == 980


class TestTaskDisplayName:
    def test_with_difficulty(self, runner: WorkerRunner):
        task = {"task_spec": {"task_type": "coding", "difficulty": "easy"}}
        assert runner._task_display_name(task) == "coding (easy)"

    def test_without_difficulty(self, runner: WorkerRunner):
        task = {"task_spec": {"task_type": "research_extraction"}}
        assert runner._task_display_name(task) == "research_extraction"

    def test_empty_spec(self, runner: WorkerRunner):
        task = {"task_spec": {}}
        assert runner._task_display_name(task) == "unknown"


class TestCLIEntryPoint:
    def test_help_no_crash(self):
        from agentrelay.worker.cli import main

        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 0

    def test_worker_no_claude(self):
        """worker subcommand fails if claude CLI not on PATH."""
        from agentrelay.worker.cli import main

        with patch("shutil.which", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                main(["worker", "--server", "http://localhost:8000"])
            assert exc_info.value.code == 1
