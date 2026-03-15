"""Worker runner — poll server, claim tasks, execute via Claude CLI, submit results."""

from __future__ import annotations

import asyncio
import logging
import platform
import os
import random
import sys
from typing import Any

import httpx

from agentrelay.worker.executor import ExecutionStatus, ExecutorConfig, WorkerExecutor

logger = logging.getLogger(__name__)

PREFIX = "[AgentRelay Worker]"


class WorkerRunner:
    """Main worker loop: register → poll → claim → execute → submit."""

    def __init__(
        self,
        server_url: str,
        *,
        agent_name: str | None = None,
        poll_interval: int = 30,
        executor_config: ExecutorConfig | None = None,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.agent_name = agent_name or f"worker-{platform.node()}-{os.getpid()}"
        self.poll_interval = poll_interval
        self.executor = WorkerExecutor(executor_config)
        self.client = httpx.AsyncClient(base_url=self.server_url, timeout=60)
        self.agent_id: str | None = None
        self.api_key: str | None = None
        self.stats = {"completed": 0, "failed": 0, "reputation": 1000}

    def _log(self, msg: str) -> None:
        print(f"{PREFIX} {msg}", flush=True)

    def _headers(self) -> dict[str, str]:
        if self.api_key:
            return {"X-API-Key": self.api_key}
        return {}

    async def _register(self) -> None:
        """Register as a worker agent. Retry with random suffix on 409."""
        name = self.agent_name
        for attempt in range(3):
            try:
                resp = await self.client.post(
                    "/agents",
                    json={
                        "name": name,
                        "capabilities": {
                            "roles": ["worker"],
                            "skills": ["data_structuring", "research_extraction", "coding"],
                        },
                        "quota_profile": {
                            "provider": "anthropic",
                            "model": "claude-code",
                            "executor_type": "cli",
                            "plan_type": "pro",
                            "daily_task_budget": 100,
                            "safe_token_cap": 50000,
                        },
                    },
                )
                if resp.status_code == 201:
                    data = resp.json()
                    self.agent_id = data["id"]
                    self.api_key = data.get("api_key", "")
                    self._log(f"Registered as {name} (id: {self.agent_id[:8]}...)")
                    return
                elif resp.status_code == 409:
                    name = f"{self.agent_name}-{random.randint(1000, 9999)}"
                    self._log(f"Name taken, retrying as {name}...")
                    continue
                else:
                    self._log(f"Registration failed: {resp.status_code} {resp.text}")
                    raise SystemExit(1)
            except httpx.ConnectError as exc:
                self._log(f"Cannot connect to {self.server_url}: {exc}")
                raise SystemExit(1)

        self._log("Registration failed after 3 attempts")
        raise SystemExit(1)

    async def _poll_tasks(self) -> list[dict[str, Any]]:
        """Fetch available tasks from server."""
        try:
            resp = await self.client.get(
                "/tasks/available",
                params={"agent_id": self.agent_id, "limit": 5},
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Poll error: %s", exc)
        return []

    async def _claim_task(self, task_id: str) -> bool:
        """Claim a task. Returns True on success."""
        try:
            resp = await self.client.post(
                f"/tasks/{task_id}/claim",
                json={"agent_id": self.agent_id},
                headers=self._headers(),
            )
            return resp.status_code == 200
        except httpx.HTTPError as exc:
            logger.warning("Claim error: %s", exc)
            return False

    async def _submit_result(self, task_id: str, output_data: dict[str, Any]) -> dict[str, Any] | None:
        """Submit task output. Returns response data or None."""
        try:
            resp = await self.client.post(
                f"/tasks/{task_id}/submit",
                json={
                    "task_id": task_id,
                    "agent_id": self.agent_id,
                    "output_data": output_data,
                },
                headers=self._headers(),
            )
            if resp.status_code == 200:
                return resp.json()
        except httpx.HTTPError as exc:
            logger.warning("Submit error: %s", exc)
        return None

    def _task_display_name(self, task: dict[str, Any]) -> str:
        """Extract a readable name from task_spec."""
        spec = task.get("task_spec", {})
        task_type = spec.get("task_type", "unknown")
        difficulty = spec.get("difficulty", "")
        return f"{task_type} ({difficulty})" if difficulty else task_type

    async def _process_task(self, task: dict[str, Any]) -> None:
        """Claim, execute, and submit a single task."""
        task_id = task["id"]
        short_id = task_id[:8]
        name = self._task_display_name(task)

        self._log(f"Found task #{short_id}: {name}")
        self._log(f"Claiming task #{short_id}...")

        if not await self._claim_task(task_id):
            self._log(f"⚠️  Could not claim task #{short_id} (already taken?)")
            return

        self._log("Running with Claude...")
        result = await self.executor.execute(task.get("task_spec", {}))

        if result.status == ExecutionStatus.SUCCESS:
            output_data = result.output_data or {"raw_output": result.output}
        elif result.status == ExecutionStatus.TIMEOUT:
            self._log(f"⏱️  Task #{short_id} timed out after {result.duration_seconds:.0f}s")
            output_data = {"error": "timeout", "raw_output": result.output}
        else:
            self._log(f"⚠️  Claude execution failed: {result.error}")
            output_data = {"error": result.error, "raw_output": result.output}

        self._log("Submitting result...")
        submit_resp = await self._submit_result(task_id, output_data)

        if submit_resp is not None:
            # Check the task status after submission
            try:
                task_resp = await self.client.get(
                    f"/tasks/{task_id}",
                    headers=self._headers(),
                )
                if task_resp.status_code == 200:
                    final_status = task_resp.json().get("status", "unknown")
                else:
                    final_status = "unknown"
            except httpx.HTTPError:
                final_status = "unknown"

            if final_status == "completed":
                self.stats["completed"] += 1
                self.stats["reputation"] += 50
                self._log(
                    f"✅ Task #{short_id} completed! "
                    f"Reputation: {self.stats['reputation']} (+50)"
                )
            elif final_status == "failed":
                self.stats["failed"] += 1
                self.stats["reputation"] = max(0, self.stats["reputation"] - 20)
                self._log(
                    f"❌ Task #{short_id} failed validation. "
                    f"Reputation: {self.stats['reputation']} (-20)"
                )
            else:
                self.stats["completed"] += 1
                self._log(f"📤 Task #{short_id} submitted (status: {final_status})")
        else:
            self._log(f"⚠️  Failed to submit task #{short_id}")

    async def run(self) -> None:
        """Main worker loop."""
        self._log(f"Connecting to {self.server_url}...")

        # Verify server is reachable
        backoff = 5
        while True:
            try:
                resp = await self.client.get("/health")
                if resp.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            self._log(f"Server not reachable. Retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

        self._log(f"Connected to {self.server_url}")
        await self._register()

        self._log(f"Polling every {self.poll_interval}s. Press Ctrl+C to stop.")

        try:
            while True:
                self._log("Checking for tasks...")
                tasks = await self._poll_tasks()

                if not tasks:
                    self._log("No tasks available. Waiting...")
                else:
                    await self._process_task(tasks[0])

                await asyncio.sleep(self.poll_interval)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            self._log(
                f"Shutting down. Stats: {self.stats['completed']} completed, "
                f"{self.stats['failed']} failed"
            )
            await self.client.aclose()
