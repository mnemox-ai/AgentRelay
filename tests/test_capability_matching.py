"""Tests for agent capability matching on task assignment."""

from __future__ import annotations

import uuid

import pytest


async def _create_agent(client, name="worker", quota_profile=None, capabilities=None) -> dict:
    payload: dict = {"name": name}
    if quota_profile is not None:
        payload["quota_profile"] = quota_profile
    if capabilities is not None:
        payload["capabilities"] = capabilities
    resp = await client.post("/agents", json=payload)
    data = resp.json()
    return {"id": data["id"], "api_key": data["api_key"]}


def _auth(api_key: str) -> dict:
    return {"X-API-Key": api_key}


async def _create_task(client, publisher: dict, task_spec=None) -> dict:
    spec = task_spec or {"type": "coding", "description": "write tests"}
    resp = await client.post(
        "/tasks",
        json={
            "task_spec": spec,
            "publisher_id": publisher["id"],
            "reward": 5.0,
        },
        headers=_auth(publisher["api_key"]),
    )
    return resp.json()


class TestCapabilityTaskTypeFilter:
    """Agent should only see tasks matching its supported_task_types."""

    @pytest.mark.asyncio
    async def test_agent_only_sees_supported_task_types(self, client):
        pub = await _create_agent(client, "pub-cap-type")

        # Create tasks with different types
        await _create_task(client, pub, {"task_type": "coding", "description": "code task"})
        await _create_task(client, pub, {"task_type": "research_extraction", "description": "research task"})
        await _create_task(client, pub, {"task_type": "data_structuring", "description": "data task"})

        # Agent only supports coding
        worker = await _create_agent(client, "worker-coding-only", capabilities={
            "supported_task_types": ["coding"],
        })

        resp = await client.get(f"/tasks/available?agent_id={worker['id']}")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 1
        assert tasks[0]["task_spec"]["task_type"] == "coding"

    @pytest.mark.asyncio
    async def test_agent_with_multiple_supported_types(self, client):
        pub = await _create_agent(client, "pub-cap-multi")

        await _create_task(client, pub, {"task_type": "coding", "description": "code"})
        await _create_task(client, pub, {"task_type": "research_extraction", "description": "research"})
        await _create_task(client, pub, {"task_type": "data_structuring", "description": "data"})

        # Agent supports coding + research
        worker = await _create_agent(client, "worker-multi", capabilities={
            "supported_task_types": ["coding", "research_extraction"],
        })

        resp = await client.get(f"/tasks/available?agent_id={worker['id']}")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 2
        types = {t["task_spec"]["task_type"] for t in tasks}
        assert types == {"coding", "research_extraction"}

    @pytest.mark.asyncio
    async def test_agent_with_no_capabilities_sees_all(self, client):
        """Empty capabilities dict = agent can do everything."""
        pub = await _create_agent(client, "pub-cap-all")

        await _create_task(client, pub, {"task_type": "coding", "description": "code"})
        await _create_task(client, pub, {"task_type": "research_extraction", "description": "research"})

        worker = await _create_agent(client, "worker-all", capabilities={})

        resp = await client.get(f"/tasks/available?agent_id={worker['id']}")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestCapabilityDifficultyFilter:
    """Agent should only see tasks with difficulty <= max_difficulty."""

    @pytest.mark.asyncio
    async def test_easy_agent_only_sees_easy_tasks(self, client):
        pub = await _create_agent(client, "pub-diff-easy")

        await _create_task(client, pub, {"task_type": "coding", "difficulty": "easy", "description": "e"})
        await _create_task(client, pub, {"task_type": "coding", "difficulty": "medium", "description": "m"})
        await _create_task(client, pub, {"task_type": "coding", "difficulty": "hard", "description": "h"})

        worker = await _create_agent(client, "worker-easy", capabilities={
            "max_difficulty": "easy",
        })

        resp = await client.get(f"/tasks/available?agent_id={worker['id']}")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 1
        assert tasks[0]["task_spec"]["difficulty"] == "easy"

    @pytest.mark.asyncio
    async def test_medium_agent_sees_easy_and_medium(self, client):
        pub = await _create_agent(client, "pub-diff-med")

        await _create_task(client, pub, {"task_type": "coding", "difficulty": "easy", "description": "e"})
        await _create_task(client, pub, {"task_type": "coding", "difficulty": "medium", "description": "m"})
        await _create_task(client, pub, {"task_type": "coding", "difficulty": "hard", "description": "h"})

        worker = await _create_agent(client, "worker-medium", capabilities={
            "max_difficulty": "medium",
        })

        resp = await client.get(f"/tasks/available?agent_id={worker['id']}")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 2
        diffs = {t["task_spec"]["difficulty"] for t in tasks}
        assert diffs == {"easy", "medium"}

    @pytest.mark.asyncio
    async def test_hard_agent_sees_all_difficulties(self, client):
        pub = await _create_agent(client, "pub-diff-hard")

        await _create_task(client, pub, {"task_type": "coding", "difficulty": "easy", "description": "e"})
        await _create_task(client, pub, {"task_type": "coding", "difficulty": "medium", "description": "m"})
        await _create_task(client, pub, {"task_type": "coding", "difficulty": "hard", "description": "h"})

        worker = await _create_agent(client, "worker-hard", capabilities={
            "max_difficulty": "hard",
        })

        resp = await client.get(f"/tasks/available?agent_id={worker['id']}")
        assert resp.status_code == 200
        assert len(resp.json()) == 3


class TestCapabilityTokenCapFilter:
    """Agent should not see tasks with token_estimate > safe_token_cap."""

    @pytest.mark.asyncio
    async def test_token_cap_filters_expensive_tasks(self, client):
        pub = await _create_agent(client, "pub-tok")

        await _create_task(client, pub, {"task_type": "coding", "token_estimate": 500, "description": "small"})
        await _create_task(client, pub, {"task_type": "coding", "token_estimate": 5000, "description": "big"})

        worker = await _create_agent(
            client, "worker-tok",
            quota_profile={"safe_token_cap": 1000},
        )

        resp = await client.get(f"/tasks/available?agent_id={worker['id']}")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 1
        assert tasks[0]["task_spec"]["token_estimate"] == 500

    @pytest.mark.asyncio
    async def test_no_token_cap_sees_all(self, client):
        """Agent without quota profile (safe_token_cap=0) should not filter by tokens."""
        pub = await _create_agent(client, "pub-notok")

        await _create_task(client, pub, {"task_type": "coding", "token_estimate": 500, "description": "s"})
        await _create_task(client, pub, {"task_type": "coding", "token_estimate": 50000, "description": "xl"})

        worker = await _create_agent(client, "worker-notok")

        resp = await client.get(f"/tasks/available?agent_id={worker['id']}")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


class TestCapabilityCombinedFilters:
    """Test type + difficulty + token filters together."""

    @pytest.mark.asyncio
    async def test_combined_filters(self, client):
        pub = await _create_agent(client, "pub-combo")

        # Should match: coding + easy + low tokens
        await _create_task(client, pub, {
            "task_type": "coding", "difficulty": "easy", "token_estimate": 500, "description": "match",
        })
        # Filtered by type (research, not coding)
        await _create_task(client, pub, {
            "task_type": "research_extraction", "difficulty": "easy", "token_estimate": 500, "description": "no-type",
        })
        # Filtered by difficulty (hard > easy)
        await _create_task(client, pub, {
            "task_type": "coding", "difficulty": "hard", "token_estimate": 500, "description": "no-diff",
        })
        # Filtered by token cap (5000 > 1000)
        await _create_task(client, pub, {
            "task_type": "coding", "difficulty": "easy", "token_estimate": 5000, "description": "no-tok",
        })

        worker = await _create_agent(
            client, "worker-combo",
            capabilities={
                "supported_task_types": ["coding"],
                "max_difficulty": "easy",
            },
            quota_profile={"safe_token_cap": 1000},
        )

        resp = await client.get(f"/tasks/available?agent_id={worker['id']}")
        assert resp.status_code == 200
        tasks = resp.json()
        assert len(tasks) == 1
        assert tasks[0]["task_spec"]["description"] == "match"


class TestAvailableWithoutAgentId:
    """GET /tasks/available without agent_id should still work as before."""

    @pytest.mark.asyncio
    async def test_no_agent_id_returns_all(self, client):
        pub = await _create_agent(client, "pub-nofilter")
        await _create_task(client, pub, {"task_type": "coding", "difficulty": "hard", "token_estimate": 99999})
        await _create_task(client, pub, {"task_type": "research_extraction", "difficulty": "easy"})

        resp = await client.get("/tasks/available")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    @pytest.mark.asyncio
    async def test_unknown_agent_id_returns_404(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/tasks/available?agent_id={fake_id}")
        assert resp.status_code == 404
