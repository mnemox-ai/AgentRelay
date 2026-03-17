"""Local E2E test: start API on SQLite → seed a task → run worker for one cycle."""

from __future__ import annotations

import asyncio
import json
import sys
import time

import httpx

SERVER_URL = "http://127.0.0.1:8765"


async def wait_for_server(timeout: float = 30) -> bool:
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient() as client:
        while time.monotonic() < deadline:
            try:
                r = await client.get(f"{SERVER_URL}/health", timeout=2)
                if r.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.ReadTimeout):
                pass
            await asyncio.sleep(0.5)
    return False


async def main() -> None:
    print("=" * 60)
    print("AgentRelay Worker E2E Test (local)")
    print("=" * 60)

    # --- Start server ---
    print("\n[1/6] Starting local API server (SQLite in-memory)...")

    import os
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
    os.environ["REDIS_URL"] = ""
    os.environ["ENABLE_REGENERATOR"] = "false"

    # Patch PostgreSQL types for SQLite
    from sqlalchemy.dialects.postgresql import JSONB, UUID
    from sqlalchemy.ext.compiler import compiles

    @compiles(JSONB, "sqlite")
    def _compile_jsonb_sqlite(type_, compiler, **kw):
        return "JSON"

    @compiles(UUID, "sqlite")
    def _compile_uuid_sqlite(type_, compiler, **kw):
        return "CHAR(32)"

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import StaticPool

    test_engine = create_async_engine("sqlite+aiosqlite://", echo=False, poolclass=StaticPool)
    test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    from agentrelay.models.base import Base
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Patch BOTH the FastAPI dependency AND the module-level session factory
    # (background loops use agentrelay.db.async_session_factory directly)
    import agentrelay.db as db_module
    db_module.async_session_factory = test_session_factory
    db_module.engine = test_engine

    from agentrelay.api.app import app
    from agentrelay.api.deps import get_db, get_rate_limiter
    from agentrelay.security.rate_limiter import RateLimiter

    async def _override_get_db():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(max_requests=10000, window_seconds=1)

    # Mock Redis for queue service
    from unittest.mock import patch as _patch, AsyncMock

    import uvicorn

    config = uvicorn.Config(app, host="127.0.0.1", port=8765, log_level="warning")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    if not await wait_for_server():
        print("  FAIL: Server did not start")
        sys.exit(1)
    print("  OK: Server running at", SERVER_URL)

    # --- Test flow ---
    async with httpx.AsyncClient(base_url=SERVER_URL, timeout=30) as client:

        # [2] Register agent
        print("\n[2/6] Registering worker agent...")
        r = await client.post("/agents", json={
            "name": "test-worker-e2e",
            "capabilities": {"roles": ["worker"], "skills": ["data_structuring"]},
            "quota_profile": {
                "provider": "anthropic", "model": "claude-code",
                "executor_type": "cli", "plan_type": "pro",
                "daily_task_budget": 10, "safe_token_cap": 50000,
            },
        })
        print(f"  Status: {r.status_code}")
        if r.status_code != 201:
            print(f"  FAIL: {r.text}")
            server.should_exit = True
            await server_task
            sys.exit(1)
        agent_data = r.json()
        agent_id = agent_data["id"]
        api_key = agent_data.get("api_key", "")
        print(f"  OK: Agent registered (id={agent_id[:8]}...)")
        print(f"  API Key: {api_key[:16]}..." if api_key else "  API Key: (none)")

        headers = {"X-API-Key": api_key} if api_key else {}

        # [3] Create a task
        print("\n[3/6] Creating a test task...")
        r = await client.post("/tasks", json={
            "task_spec": {
                "task_type": "data_structuring",
                "difficulty": "easy",
                "input_data": {
                    "instruction": "Convert this CSV row to JSON: name,age,city\\nAlice,30,Taipei",
                },
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                        "city": {"type": "string"},
                    },
                    "required": ["name", "age", "city"],
                },
                "validation_rules": [],
            },
            "publisher_id": agent_id,
            "reward_amount": 10,
        }, headers=headers)
        print(f"  Status: {r.status_code}")
        if r.status_code not in (200, 201):
            print(f"  FAIL: {r.text}")
            server.should_exit = True
            await server_task
            sys.exit(1)
        task_data = r.json()
        task_id = task_data["id"]
        print(f"  OK: Task created (id={task_id[:8]}...)")

        # [4] Poll available tasks
        print("\n[4/6] Polling available tasks...")
        r = await client.get("/tasks/available", params={"agent_id": agent_id, "limit": 5}, headers=headers)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            tasks = r.json()
            print(f"  Available tasks: {len(tasks)}")
        else:
            print(f"  Response: {r.text[:200]}")

        # [5] Claim task
        print("\n[5/6] Claiming task...")
        r = await client.post(f"/tasks/{task_id}/claim", json={"agent_id": agent_id}, headers=headers)
        print(f"  Status: {r.status_code}")
        if r.status_code != 200:
            print(f"  Response: {r.text[:300]}")

        # [6] Execute with claude CLI and submit
        print("\n[6/6] Executing with Claude CLI...")
        from agentrelay.worker.executor import ExecutorConfig, WorkerExecutor

        executor = WorkerExecutor(ExecutorConfig(timeout_seconds=60))
        task_spec = task_data.get("task_spec", {})
        prompt = executor._build_prompt(task_spec)
        print(f"  Prompt:\n    {prompt[:300]}")

        result = await executor.execute(task_spec)
        print(f"  Execution status: {result.status.value}")
        print(f"  Duration: {result.duration_seconds:.1f}s")
        print(f"  Raw output: {result.output[:300].encode('ascii', 'replace').decode()}")
        if result.error:
            print(f"  Error: {result.error}")
        if result.output_data:
            print(f"  Parsed JSON: {json.dumps(result.output_data, indent=2)}")
        else:
            print("  WARNING: Could not parse JSON from output")

        # Submit
        print("\n  Submitting result...")
        output_data = result.output_data or {"raw_output": result.output}
        r = await client.post(f"/tasks/{task_id}/submit", json={
            "task_id": task_id,
            "agent_id": agent_id,
            "output_data": output_data,
        }, headers=headers)
        print(f"  Submit status: {r.status_code}")
        if r.status_code == 200:
            submit_resp = r.json()
            print(f"  Submit response: {json.dumps(submit_resp, indent=2)[:500]}")
        else:
            print(f"  Submit error: {r.text[:300]}")

        # Check final task status
        r = await client.get(f"/tasks/{task_id}", headers=headers)
        if r.status_code == 200:
            final = r.json()
            status = final.get("status", "unknown")
            print(f"\n  FINAL TASK STATUS: {status}")
            if status == "completed":
                print("  >>> FULL LIFECYCLE PASS <<<")
            elif status == "failed":
                print("  >>> VALIDATION FAILED (check output_schema match) <<<")
            else:
                print(f"  >>> UNEXPECTED STATUS: {status} <<<")

    # Shutdown
    server.should_exit = True
    await server_task
    print("\n" + "=" * 60)
    print("E2E test complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
