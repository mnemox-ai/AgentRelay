"""Seed AgentRelay on Render: register agents + create tasks via REST API.

Targets the production Render URL by default.

Usage:
    python scripts/render_seed.py                              # 20 tasks
    python scripts/render_seed.py 50                           # 50 random tasks
    python scripts/render_seed.py 10 coding                    # 10 coding tasks
    python scripts/render_seed.py https://custom-url.com 30    # custom URL + 30 tasks

Environment:
    AGENTRELAY_URL  — override the base URL (default: https://agentrelay-api.onrender.com)
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx

sys.path.insert(0, "src")

from agentrelay.tasks.generator import generate_tasks  # noqa: E402

RENDER_URL = "https://agentrelay-api.onrender.com"

AGENTS = [
    {
        "name": "alpha-publisher",
        "quota_profile": {
            "provider": "anthropic",
            "model": "claude-3-haiku",
            "executor_type": "llm",
            "plan_type": "free",
            "daily_task_budget": 100,
            "safe_token_cap": 5000,
        },
        "capabilities": {"roles": ["publisher"]},
    },
    {
        "name": "beta-worker",
        "quota_profile": {
            "provider": "anthropic",
            "model": "claude-3-haiku",
            "executor_type": "llm",
            "plan_type": "free",
            "daily_task_budget": 50,
            "safe_token_cap": 3000,
        },
        "capabilities": {
            "roles": ["worker"],
            "skills": ["data_structuring", "research_extraction"],
        },
    },
    {
        "name": "gamma-coder",
        "quota_profile": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "executor_type": "llm",
            "plan_type": "free",
            "daily_task_budget": 30,
            "safe_token_cap": 5000,
        },
        "capabilities": {"roles": ["worker"], "skills": ["coding"]},
    },
    {
        "name": "delta-writer",
        "quota_profile": {
            "provider": "anthropic",
            "model": "claude-3-haiku",
            "executor_type": "llm",
            "plan_type": "free",
            "daily_task_budget": 40,
            "safe_token_cap": 4000,
        },
        "capabilities": {
            "roles": ["worker"],
            "skills": ["content_generation"],
        },
    },
    {
        "name": "epsilon-classifier",
        "quota_profile": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "executor_type": "llm",
            "plan_type": "free",
            "daily_task_budget": 60,
            "safe_token_cap": 2000,
        },
        "capabilities": {
            "roles": ["worker"],
            "skills": ["classification"],
        },
    },
]


async def register_agents(client: httpx.AsyncClient) -> dict[str, dict]:
    agents: dict[str, dict] = {}
    for agent_data in AGENTS:
        resp = await client.post("/agents", json=agent_data)
        if resp.status_code == 409:
            print(f"  Skipped (already exists): {agent_data['name']}")
            continue
        resp.raise_for_status()
        result = resp.json()
        agents[result["name"]] = result
        print(f"  Registered: {result['name']} (id={result['id'][:8]}...)")
    return agents


async def create_tasks(
    client: httpx.AsyncClient,
    publisher: dict,
    *,
    count: int | None = None,
    task_type: str | None = None,
) -> list[dict]:
    tasks_data = generate_tasks(
        publisher_id=publisher["id"],
        count=count,
        task_type=task_type,
    )
    headers = {"X-Api-Key": publisher["api_key"]}

    created: list[dict] = []
    for i, body in enumerate(tasks_data):
        resp = await client.post("/tasks", json=body, headers=headers)
        resp.raise_for_status()
        result = resp.json()
        created.append(result)
        tt = body["task_spec"]["task_type"]
        diff = body["task_spec"]["difficulty"]
        print(f"  [{i}] {tt}/{diff} — reward=${result['reward']:.2f} (id={result['id'][:8]}...)")
    return created


async def main() -> None:
    base_url = os.environ.get("AGENTRELAY_URL", RENDER_URL)
    count: int | None = None
    task_type: str | None = None

    for arg in sys.argv[1:]:
        if arg.startswith("http"):
            base_url = arg
        elif arg.isdigit():
            count = int(arg)
        else:
            task_type = arg

    print(f"Target: {base_url}")

    async with httpx.AsyncClient(base_url=base_url, timeout=60) as client:
        # Health check (Render cold start can be slow)
        print("Checking health...")
        try:
            resp = await client.get("/health")
            resp.raise_for_status()
            print(f"  OK: {resp.json()}")
        except (httpx.ConnectError, httpx.ReadTimeout) as e:
            print(f"ERROR: Cannot reach {base_url} — {e}")
            sys.exit(1)

        print(f"\n=== Registering {len(AGENTS)} agents ===")
        agents = await register_agents(client)

        if "alpha-publisher" not in agents:
            print("ERROR: alpha-publisher not registered (maybe already exists).")
            print("  If re-seeding, delete existing agents first or use seed_tasks.py locally.")
            sys.exit(1)

        desc = f"{count or 20} tasks"
        if task_type:
            desc += f" (type={task_type})"
        print(f"\n=== Creating {desc} ===")
        publisher = agents["alpha-publisher"]
        tasks = await create_tasks(client, publisher, count=count, task_type=task_type)

        print(f"\nDone: {len(agents)} agents, {len(tasks)} tasks created on {base_url}")
        print("\nAgent API keys (save these — shown once):")
        for name, agent in agents.items():
            print(f"  {name}: {agent['api_key']}")


if __name__ == "__main__":
    asyncio.run(main())
