"""Tests for agent API routes."""

from __future__ import annotations

import uuid

import pytest


class TestRegisterAgent:
    @pytest.mark.asyncio
    async def test_register_success(self, client):
        resp = await client.post("/agents", json={"name": "bot-1"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "bot-1"
        assert data["status"] == "active"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_register_with_capabilities(self, client):
        resp = await client.post(
            "/agents",
            json={
                "name": "bot-2",
                "capabilities": {"languages": ["python"]},
                "quota_profile": {"provider": "anthropic"},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["capabilities"] == {"languages": ["python"]}
        assert data["quota_profile"] == {"provider": "anthropic"}

    @pytest.mark.asyncio
    async def test_register_duplicate_name(self, client):
        await client.post("/agents", json={"name": "dup-bot"})
        resp = await client.post("/agents", json={"name": "dup-bot"})
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"]


class TestGetAgent:
    @pytest.mark.asyncio
    async def test_get_existing(self, client):
        create_resp = await client.post("/agents", json={"name": "lookup-bot"})
        agent_id = create_resp.json()["id"]

        resp = await client.get(f"/agents/{agent_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "lookup-bot"

    @pytest.mark.asyncio
    async def test_get_not_found(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/agents/{fake_id}")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]
