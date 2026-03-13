"""AgentRelay — Full Lifecycle Demo

Runs the complete task lifecycle:
  1. Register 3 agents
  2. Publish 10 tasks
  3. Agents claim tasks
  4. Agents submit outputs (7 pass, 3 intentionally fail)
  5. Validation pipeline runs automatically
  6. Check reputation and dashboard stats

Usage:
    docker compose up -d
    python scripts/seed_and_run.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx

# Import shared data from seed_tasks
sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_tasks import AGENTS, BASE_URL, SEED_TASKS, create_tasks, register_agents

# ---------------------------------------------------------------------------
# Mock outputs — simulates agent work products
# Tasks 2, 6, 9 intentionally fail validation (missing required fields)
# ---------------------------------------------------------------------------
MOCK_OUTPUTS: list[dict] = [
    # [0] Apple Q4 — PASS (schema: company, quarter, revenue_usd, net_income_usd)
    {
        "company": "Apple Inc.",
        "quarter": "Q4 2025",
        "revenue_usd": 95_400_000_000,
        "net_income_usd": 24_100_000_000,
        "segments": [{"name": "iPhone", "revenue_usd": 48_700_000_000}],
    },
    # [1] Product specs — PASS (schema: product_name, price_usd, rating, specs)
    {
        "product_name": "Wireless Mouse X1",
        "price_usd": 29.99,
        "rating": 4.5,
        "review_count": 1203,
        "specs": {
            "battery": "2x AA, 12 months",
            "connectivity": "2.4GHz USB dongle",
            "weight": "85g",
            "dpi": [800, 1200, 1600],
        },
    },
    # [2] Clinical trial — FAIL (missing required "results")
    {
        "trial_id": "NCT00001234",
        "phase": 3,
        "drug": "Examplivir",
        "dosage": "200mg",
        "sample_size": 1240,
        "primary_endpoint": "viral load reduction at week 12",
        # "results" intentionally omitted
        "safety": {"sae_treatment": "3.2%", "sae_placebo": "2.9%"},
    },
    # [3] Tokyo population — PASS (schema: answer, source_description)
    {
        "answer": "Approximately 37.4 million in the greater metropolitan area",
        "source_description": "UN World Urbanization Prospects 2024",
        "confidence": 0.85,
    },
    # [4] Python frameworks — PASS (schema: frameworks array)
    {
        "frameworks": [
            {
                "name": "FastAPI",
                "github_stars": 79000,
                "latest_release": "0.115.0",
                "features": ["async", "OpenAPI", "type hints", "dependency injection"],
            },
            {
                "name": "Starlette",
                "github_stars": 10200,
                "latest_release": "0.41.0",
                "features": ["async", "WebSocket", "GraphQL", "middleware"],
            },
            {
                "name": "Sanic",
                "github_stars": 18100,
                "latest_release": "23.12.1",
                "features": ["async", "blueprints", "streaming", "middleware"],
            },
        ],
    },
    # [5] PostgreSQL 16 vs 17 — PASS (schema: differences array)
    {
        "differences": [
            {
                "category": "Performance",
                "description": "Improved incremental sort and query planning",
                "pg16": "Standard planner optimizations",
                "pg17": "Incremental sort for more query patterns",
            },
            {
                "category": "SQL Features",
                "description": "Enhanced JSON support",
                "pg16": "Basic JSON/JSONB operations",
                "pg17": "SQL/JSON standard functions (JSON_TABLE, etc.)",
            },
            {
                "category": "Logical Replication",
                "description": "Failover and subscriber improvements",
                "pg16": "Basic logical replication",
                "pg17": "Failover slots, subscriber apply workers",
            },
        ],
    },
    # [6] WebAssembly — FAIL (missing required "use_cases")
    {
        "summary": (
            "WebAssembly is gaining traction for server-side use, "
            "with runtimes like Wasmtime and Wasmer enabling near-native "
            "performance for polyglot workloads."
        ),
        "runtimes": [
            {
                "name": "Wasmtime",
                "description": "Bytecode Alliance reference runtime, production-grade",
                "languages": ["Rust", "C", "C++", "Go"],
            },
            {
                "name": "Wasmer",
                "description": "Universal runtime with multiple backends",
                "languages": ["Rust", "Python", "Go", "JavaScript"],
            },
            {
                "name": "WasmEdge",
                "description": "Cloud-native runtime optimized for edge computing",
                "languages": ["Rust", "C", "JavaScript", "Go"],
            },
        ],
        # "use_cases" intentionally omitted
    },
    # [7] Flatten function — PASS (schema: code)
    {
        "code": (
            "def flatten(nested_list):\n"
            "    result = []\n"
            "    for item in nested_list:\n"
            "        if isinstance(item, list):\n"
            "            result.extend(flatten(item))\n"
            "        else:\n"
            "            result.append(item)\n"
            "    return result"
        ),
        "explanation": "Recursive approach — checks each element and flattens sublists.",
    },
    # [8] LRU cache — PASS (schema: code, test_code)
    {
        "code": (
            "from collections import OrderedDict\n\n"
            "class LRUCache:\n"
            "    def __init__(self, max_size: int):\n"
            "        self._cache = OrderedDict()\n"
            "        self._max_size = max_size\n\n"
            "    def get(self, key):\n"
            "        if key not in self._cache:\n"
            "            return None\n"
            "        self._cache.move_to_end(key)\n"
            "        return self._cache[key]\n\n"
            "    def put(self, key, value):\n"
            "        if key in self._cache:\n"
            "            self._cache.move_to_end(key)\n"
            "        self._cache[key] = value\n"
            "        if len(self._cache) > self._max_size:\n"
            "            self._cache.popitem(last=False)"
        ),
        "test_code": (
            "cache = LRUCache(2)\n"
            "cache.put('a', 1)\n"
            "cache.put('b', 2)\n"
            "assert cache.get('a') == 1\n"
            "cache.put('c', 3)  # evicts 'b'\n"
            "assert cache.get('b') is None\n"
            "assert cache.get('c') == 3"
        ),
        "time_complexity": "O(1) for both get and put",
    },
    # [9] Rate limiter — FAIL (missing required "test_code")
    {
        "code": (
            "import asyncio\nimport time\n\n"
            "class TokenBucket:\n"
            "    def __init__(self, rate: float, burst: int):\n"
            "        self.rate = rate\n"
            "        self.burst = burst\n"
            "        self.tokens = float(burst)\n"
            "        self._last = time.monotonic()\n\n"
            "    def _refill(self):\n"
            "        now = time.monotonic()\n"
            "        self.tokens = min(self.burst, self.tokens + (now - self._last) * self.rate)\n"
            "        self._last = now\n\n"
            "    def try_acquire(self) -> bool:\n"
            "        self._refill()\n"
            "        if self.tokens >= 1:\n"
            "            self.tokens -= 1\n"
            "            return True\n"
            "        return False\n\n"
            "    async def acquire(self):\n"
            "        while not self.try_acquire():\n"
            "            await asyncio.sleep(1.0 / self.rate)"
        ),
        "explanation": "Token bucket with async acquire and sync try_acquire.",
        # "test_code" intentionally omitted
    },
]

# Task assignment: which agent handles which task indexes
ASSIGNMENTS = {
    "beta-worker": list(range(7)),   # tasks 0-6 (data + research)
    "gamma-coder": list(range(7, 10)),  # tasks 7-9 (coding)
}

EXPECTED_PASS = {0, 1, 3, 4, 5, 7, 8}
EXPECTED_FAIL = {2, 6, 9}


async def claim_tasks(
    client: httpx.AsyncClient,
    agents: dict[str, dict],
    tasks: list[dict],
) -> None:
    """Agents claim their assigned tasks."""
    for agent_name, task_indexes in ASSIGNMENTS.items():
        agent = agents[agent_name]
        headers = {"X-Api-Key": agent["api_key"]}
        for idx in task_indexes:
            task = tasks[idx]
            resp = await client.post(
                f"/tasks/{task['id']}/claim",
                json={"agent_id": agent["id"]},
                headers=headers,
            )
            resp.raise_for_status()
            task_type = task["task_spec"]["task_type"]
            print(f"  [{idx}] {agent_name} claimed {task_type}/{task['task_spec']['difficulty']}")


async def submit_tasks(
    client: httpx.AsyncClient,
    agents: dict[str, dict],
    tasks: list[dict],
) -> list[dict]:
    """Submit mock outputs for all claimed tasks. Returns submission responses."""
    submissions: list[dict] = []
    for agent_name, task_indexes in ASSIGNMENTS.items():
        agent = agents[agent_name]
        headers = {"X-Api-Key": agent["api_key"]}
        for idx in task_indexes:
            task = tasks[idx]
            body = {
                "task_id": task["id"],
                "agent_id": agent["id"],
                "output_data": MOCK_OUTPUTS[idx],
            }
            resp = await client.post(
                f"/tasks/{task['id']}/submit",
                json=body,
                headers=headers,
            )
            resp.raise_for_status()
            result = resp.json()
            submissions.append({"index": idx, "submission": result, "agent": agent_name})

            expected = "PASS" if idx in EXPECTED_PASS else "FAIL"
            print(f"  [{idx}] {agent_name} submitted (expected: {expected})")
    return submissions


async def check_validation(
    client: httpx.AsyncClient,
    submissions: list[dict],
) -> dict[str, int]:
    """Query validation results for each submission. Returns pass/fail counts."""
    passed = 0
    failed = 0
    for entry in submissions:
        idx = entry["index"]
        sub_id = entry["submission"]["id"]
        resp = await client.get(f"/submissions/{sub_id}/validation")
        resp.raise_for_status()
        runs = resp.json()

        all_passed = all(r["passed"] for r in runs) if runs else False
        score = min((r["score"] for r in runs), default=0.0)
        status = "PASS" if all_passed else "FAIL"
        expected = "PASS" if idx in EXPECTED_PASS else "FAIL"
        match = "OK" if status == expected else "MISMATCH"

        if all_passed:
            passed += 1
        else:
            failed += 1

        validators = ", ".join(f"{r['validator_type']}={'OK' if r['passed'] else 'FAIL'}" for r in runs)
        print(f"  [{idx}] {status} (score={score:.1f}) [{match}] — {validators}")

    return {"passed": passed, "failed": failed}


async def check_reputation(
    client: httpx.AsyncClient,
    agents: dict[str, dict],
) -> None:
    """Query reputation for each worker agent."""
    for name in ["beta-worker", "gamma-coder"]:
        agent = agents[name]
        resp = await client.get(f"/dashboard/agents/{agent['id']}/reputation")
        if resp.status_code == 404:
            print(f"  {name}: no reputation data yet")
            continue
        resp.raise_for_status()
        rep = resp.json()
        metrics = rep.get("metrics", {})
        print(
            f"  {name}: quality={metrics.get('quality_score', 0):.2f}  "
            f"pass_rate={metrics.get('pass_rate', 0):.0%}  "
            f"submissions={metrics.get('total_submissions', 0)}"
        )


async def check_task_statuses(
    client: httpx.AsyncClient,
    tasks: list[dict],
) -> None:
    """Re-fetch tasks to show final statuses."""
    for i, task in enumerate(tasks):
        resp = await client.get(f"/tasks/{task['id']}")
        resp.raise_for_status()
        t = resp.json()
        task_type = t["task_spec"]["task_type"]
        print(f"  [{i}] {task_type}/{t['task_spec']['difficulty']}: {t['status']}  reward=${t['reward']:.2f}")


async def check_dashboard(
    client: httpx.AsyncClient,
) -> None:
    """Query dashboard endpoints to verify real data."""
    # Stats
    resp = await client.get("/dashboard/stats")
    resp.raise_for_status()
    stats = resp.json()
    print(f"  Total tasks:     {stats['total_tasks']}")
    print(f"  Completed tasks: {stats['completed_tasks']}")
    print(f"  Active agents:   {stats['active_agents']}")
    print(f"  Total rewards:   ${stats['total_rewards']:.2f}")

    # Validation rate
    resp = await client.get("/dashboard/validation-rate")
    resp.raise_for_status()
    vr = resp.json()
    print(f"  Validation rate: {vr['passed']}/{vr['total']} ({vr['rate']:.1f}%)")

    # Top agents
    resp = await client.get("/dashboard/agents/top")
    resp.raise_for_status()
    top = resp.json()
    if top:
        print("  Top agents:")
        for a in top:
            print(f"    {a['name']}: quality={a['quality_score']:.2f}  pass_rate={a['pass_rate']:.0%}")

    # Ledger for each worker
    print("  Ledger entries:")
    for name in ["beta-worker", "gamma-coder"]:
        resp = await client.get("/dashboard/agents/top")
        # We need agent IDs — get from /agents top list
        break
    # Ledger is checked per-agent in the reputation section above


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

        print("=" * 60)
        print(" AgentRelay — Full Lifecycle Demo")
        print("=" * 60)

        # Phase 1: Register agents
        print("\n[Phase 1] Registering 3 agents...")
        agents = await register_agents(client)

        # Phase 2: Create tasks
        print(f"\n[Phase 2] Creating {len(SEED_TASKS)} tasks...")
        publisher = agents["alpha-publisher"]
        tasks = await create_tasks(client, publisher)

        # Phase 3: Claim
        print("\n[Phase 3] Agents claiming tasks...")
        await claim_tasks(client, agents, tasks)

        # Phase 4: Submit
        print("\n[Phase 4] Submitting outputs (7 valid, 3 intentionally bad)...")
        submissions = await submit_tasks(client, agents, tasks)

        # Phase 5: Validation results
        print("\n[Phase 5] Validation results:")
        counts = await check_validation(client, submissions)
        print(f"  --- {counts['passed']} passed, {counts['failed']} failed ---")

        # Phase 6: Task statuses
        print("\n[Phase 6] Final task statuses:")
        await check_task_statuses(client, tasks)

        # Phase 7: Reputation
        print("\n[Phase 7] Agent reputation:")
        await check_reputation(client, agents)

        # Phase 8: Dashboard stats
        print("\n[Phase 8] Dashboard stats (GET /dashboard/*):")
        await check_dashboard(client)

        # Ledger details
        print("\n[Phase 9] Ledger entries:")
        for name in ["beta-worker", "gamma-coder"]:
            agent = agents[name]
            resp = await client.get(f"/dashboard/agents/{agent['id']}/ledger")
            resp.raise_for_status()
            entries = resp.json()
            total = sum(e["amount"] if e["entry_type"] == "reward" else -abs(e["amount"]) for e in entries)
            print(f"  {name}: {len(entries)} entries, net=${total:.2f}")
            for e in entries:
                sign = "+" if e["entry_type"] == "reward" else "-"
                print(f"    {e['entry_type']:>7} {sign}${abs(e['amount']):.2f}")

        print("\n" + "=" * 60)
        print(" Demo complete. Dashboard: http://localhost:3000/dashboard")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
