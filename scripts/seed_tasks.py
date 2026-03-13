"""Seed script: register 3 agents and create 10 tasks via the AgentRelay API.

Usage:
    docker compose up -d
    python scripts/seed_tasks.py
"""

from __future__ import annotations

import asyncio
import sys

import httpx

BASE_URL = "http://localhost:8000"

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
]

SEED_TASKS = [
    # --- data_structuring (3) ---
    {
        "task_spec": {
            "task_type": "data_structuring",
            "difficulty": "easy",
            "input_data": {
                "raw_text": (
                    "Apple Inc. reported Q4 2025 revenue of $95.4B, up 8% YoY. "
                    "Net income was $24.1B. iPhone revenue was $48.7B."
                ),
            },
            "output_schema": {
                "type": "object",
                "required": ["company", "quarter", "revenue_usd", "net_income_usd"],
                "properties": {
                    "company": {"type": "string"},
                    "quarter": {"type": "string"},
                    "revenue_usd": {"type": "number"},
                    "net_income_usd": {"type": "number"},
                    "segments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "revenue_usd": {"type": "number"},
                            },
                        },
                    },
                },
            },
            "validation_method": "schema",
            "token_estimate": 500,
        },
        "reward": 0.05,
        "deadline_seconds": 3600,
    },
    {
        "task_spec": {
            "task_type": "data_structuring",
            "difficulty": "medium",
            "input_data": {
                "raw_text": (
                    "Product: Wireless Mouse X1\nPrice: $29.99\n"
                    "Rating: 4.5/5 (1,203 reviews)\n"
                    "Battery: 2x AA, lasts 12 months\n"
                    "Connectivity: 2.4GHz USB dongle\nWeight: 85g\n"
                    "DPI: 800/1200/1600"
                ),
            },
            "output_schema": {
                "type": "object",
                "required": ["product_name", "price_usd", "rating", "specs"],
                "properties": {
                    "product_name": {"type": "string"},
                    "price_usd": {"type": "number"},
                    "rating": {"type": "number"},
                    "review_count": {"type": "integer"},
                    "specs": {"type": "object"},
                },
            },
            "validation_method": "schema",
            "token_estimate": 600,
        },
        "reward": 0.08,
        "deadline_seconds": 3600,
    },
    {
        "task_spec": {
            "task_type": "data_structuring",
            "difficulty": "hard",
            "input_data": {
                "raw_text": (
                    "Clinical Trial NCT00001234: Phase 3, randomized, double-blind. "
                    "Drug: Examplivir 200mg vs placebo. N=1,240 (620/group). "
                    "Primary endpoint: viral load reduction at week 12. "
                    "Results: -2.8 log10 vs -0.3 log10 (p<0.001). "
                    "SAEs: 3.2% vs 2.9%. Completion rate: 89%."
                ),
            },
            "output_schema": {
                "type": "object",
                "required": [
                    "trial_id", "phase", "drug", "sample_size",
                    "primary_endpoint", "results",
                ],
                "properties": {
                    "trial_id": {"type": "string"},
                    "phase": {"type": "integer"},
                    "drug": {"type": "string"},
                    "dosage": {"type": "string"},
                    "sample_size": {"type": "integer"},
                    "primary_endpoint": {"type": "string"},
                    "results": {"type": "object"},
                    "safety": {"type": "object"},
                },
            },
            "validation_method": "schema",
            "token_estimate": 1000,
        },
        "reward": 0.15,
        "deadline_seconds": 3600,
    },
    # --- research_extraction (4) ---
    {
        "task_spec": {
            "task_type": "research_extraction",
            "difficulty": "easy",
            "input_data": {
                "query": "What is the current population of Tokyo metropolitan area?",
                "context": "Based on publicly available demographic data.",
            },
            "output_schema": {
                "type": "object",
                "required": ["answer", "source_description"],
                "properties": {
                    "answer": {"type": "string"},
                    "source_description": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
            "validation_method": "rule",
            "token_estimate": 300,
        },
        "reward": 0.03,
        "deadline_seconds": 3600,
    },
    {
        "task_spec": {
            "task_type": "research_extraction",
            "difficulty": "medium",
            "input_data": {
                "query": (
                    "Compare the top 3 Python async web frameworks "
                    "by GitHub stars, latest release date, and key features."
                ),
                "context": "Focus on FastAPI, Starlette, and Sanic.",
            },
            "output_schema": {
                "type": "object",
                "required": ["frameworks"],
                "properties": {
                    "frameworks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "github_stars", "features"],
                            "properties": {
                                "name": {"type": "string"},
                                "github_stars": {"type": "integer"},
                                "latest_release": {"type": "string"},
                                "features": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
            "validation_method": "schema",
            "token_estimate": 800,
        },
        "reward": 0.10,
        "deadline_seconds": 3600,
    },
    {
        "task_spec": {
            "task_type": "research_extraction",
            "difficulty": "medium",
            "input_data": {
                "query": "List the key differences between PostgreSQL 16 and PostgreSQL 17.",
                "context": "Focus on performance improvements and new SQL features.",
            },
            "output_schema": {
                "type": "object",
                "required": ["differences"],
                "properties": {
                    "differences": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["category", "description"],
                            "properties": {
                                "category": {"type": "string"},
                                "description": {"type": "string"},
                                "pg16": {"type": "string"},
                                "pg17": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "validation_method": "schema",
            "token_estimate": 700,
        },
        "reward": 0.08,
        "deadline_seconds": 3600,
    },
    {
        "task_spec": {
            "task_type": "research_extraction",
            "difficulty": "hard",
            "input_data": {
                "query": (
                    "Summarize the current state of WebAssembly adoption "
                    "in server-side applications."
                ),
                "context": (
                    "Include runtime options (Wasmtime, Wasmer, WasmEdge), "
                    "language support, and production use cases."
                ),
            },
            "output_schema": {
                "type": "object",
                "required": ["summary", "runtimes", "use_cases"],
                "properties": {
                    "summary": {"type": "string"},
                    "runtimes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "description"],
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "languages": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                    "use_cases": {"type": "array", "items": {"type": "string"}},
                },
            },
            "validation_method": "schema",
            "token_estimate": 1200,
        },
        "reward": 0.18,
        "deadline_seconds": 3600,
    },
    # --- coding (3) ---
    {
        "task_spec": {
            "task_type": "coding",
            "difficulty": "easy",
            "input_data": {
                "language": "python",
                "task": (
                    "Write a function `flatten(nested_list)` that flattens "
                    "an arbitrarily nested list."
                ),
                "examples": [
                    {"input": [[1, 2], [3, [4, 5]]], "output": [1, 2, 3, 4, 5]},
                    {"input": [1, [2, [3, [4]]]], "output": [1, 2, 3, 4]},
                ],
            },
            "output_schema": {
                "type": "object",
                "required": ["code"],
                "properties": {
                    "code": {"type": "string"},
                    "explanation": {"type": "string"},
                },
            },
            "validation_method": "rule",
            "token_estimate": 400,
        },
        "reward": 0.05,
        "deadline_seconds": 3600,
    },
    {
        "task_spec": {
            "task_type": "coding",
            "difficulty": "medium",
            "input_data": {
                "language": "python",
                "task": (
                    "Implement a simple LRU cache class with `get(key)` and "
                    "`put(key, value)` methods. "
                    "The cache should have a configurable max size."
                ),
                "constraints": ["O(1) for both get and put", "Use only stdlib"],
            },
            "output_schema": {
                "type": "object",
                "required": ["code", "test_code"],
                "properties": {
                    "code": {"type": "string"},
                    "test_code": {"type": "string"},
                    "time_complexity": {"type": "string"},
                },
            },
            "validation_method": "rule",
            "token_estimate": 800,
        },
        "reward": 0.12,
        "deadline_seconds": 3600,
    },
    {
        "task_spec": {
            "task_type": "coding",
            "difficulty": "hard",
            "input_data": {
                "language": "python",
                "task": (
                    "Write an async rate limiter using the token bucket algorithm. "
                    "It should support `async acquire()` that waits until a token "
                    "is available, and `try_acquire()` that returns immediately."
                ),
                "constraints": [
                    "asyncio only, no external deps",
                    "Configurable rate (tokens/sec) and burst size",
                    "Thread-safe not required (single event loop)",
                ],
            },
            "output_schema": {
                "type": "object",
                "required": ["code", "test_code"],
                "properties": {
                    "code": {"type": "string"},
                    "test_code": {"type": "string"},
                    "explanation": {"type": "string"},
                },
            },
            "validation_method": "rule",
            "token_estimate": 1500,
        },
        "reward": 0.25,
        "deadline_seconds": 3600,
    },
]


async def register_agents(
    client: httpx.AsyncClient,
) -> dict[str, dict]:
    """Register all agents via POST /agents. Returns {name: response_dict}."""
    agents: dict[str, dict] = {}
    for agent_data in AGENTS:
        resp = await client.post("/agents", json=agent_data)
        resp.raise_for_status()
        result = resp.json()
        agents[result["name"]] = result
        print(f"  Registered: {result['name']} (id={result['id'][:8]}...)")
    return agents


async def create_tasks(
    client: httpx.AsyncClient,
    publisher: dict,
) -> list[dict]:
    """Create all seed tasks via POST /tasks. Returns list of task responses."""
    tasks: list[dict] = []
    headers = {"X-Api-Key": publisher["api_key"]}

    for i, task_data in enumerate(SEED_TASKS):
        body = {
            "task_spec": task_data["task_spec"],
            "publisher_id": publisher["id"],
            "reward": task_data["reward"],
            "deadline_seconds": task_data["deadline_seconds"],
        }
        resp = await client.post("/tasks", json=body, headers=headers)
        resp.raise_for_status()
        result = resp.json()
        tasks.append(result)
        task_type = task_data["task_spec"]["task_type"]
        difficulty = task_data["task_spec"]["difficulty"]
        print(f"  [{i}] {task_type}/{difficulty} — reward=${result['reward']:.2f} (id={result['id'][:8]}...)")
    return tasks


async def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else BASE_URL
    async with httpx.AsyncClient(base_url=base_url, timeout=30) as client:
        # Health check
        try:
            resp = await client.get("/health")
            resp.raise_for_status()
        except httpx.ConnectError:
            print(f"ERROR: Cannot connect to {base_url}. Is the server running?")
            print("  Run: docker compose up -d")
            sys.exit(1)

        print("=== Registering 3 agents ===")
        agents = await register_agents(client)

        print(f"\n=== Creating {len(SEED_TASKS)} tasks ===")
        publisher = agents["alpha-publisher"]
        tasks = await create_tasks(client, publisher)

        # Summary
        print(f"\nDone: {len(agents)} agents, {len(tasks)} tasks created.")
        print("\nAgent API keys (save these — shown once):")
        for name, agent in agents.items():
            print(f"  {name}: {agent['api_key']}")


if __name__ == "__main__":
    asyncio.run(main())
