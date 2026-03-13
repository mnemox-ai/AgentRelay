"""Tests for in-memory sliding-window rate limiter."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from agentrelay.security.rate_limiter import RateLimiter


class TestRateLimiterUnit:
    """Pure unit tests for the RateLimiter class."""

    def test_allows_under_limit(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            assert limiter.check("client-a") is True

    def test_blocks_over_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            assert limiter.check("client-a") is True
        assert limiter.check("client-a") is False

    def test_separate_clients_independent(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.check("a") is True
        assert limiter.check("a") is True
        assert limiter.check("a") is False
        # Different client should still be allowed
        assert limiter.check("b") is True

    def test_window_expiry_restores_access(self):
        limiter = RateLimiter(max_requests=2, window_seconds=10)

        base = 1000.0
        with patch("agentrelay.security.rate_limiter.time.monotonic", return_value=base):
            assert limiter.check("c") is True
            assert limiter.check("c") is True
            assert limiter.check("c") is False

        # Advance past the window
        with patch("agentrelay.security.rate_limiter.time.monotonic", return_value=base + 11):
            assert limiter.check("c") is True

    def test_retry_after_returns_positive_int(self):
        limiter = RateLimiter(max_requests=1, window_seconds=30)
        limiter.check("x")
        retry = limiter.retry_after("x")
        assert isinstance(retry, int)
        assert retry >= 1

    def test_retry_after_empty_bucket(self):
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.retry_after("nobody") == 0


class TestRateLimitAPI:
    """Integration tests hitting the FastAPI app with a strict rate limiter."""

    @pytest.mark.asyncio
    async def test_authenticated_endpoint_rate_limited(self, client):
        """Authenticated endpoints should return 429 when limit exceeded."""
        from agentrelay.api.app import app
        from agentrelay.api.deps import get_rate_limiter

        strict = RateLimiter(max_requests=2, window_seconds=60)
        app.dependency_overrides[get_rate_limiter] = lambda: strict

        try:
            # Register an agent
            resp = await client.post("/agents", json={"name": "rl-agent"})
            agent = resp.json()
            headers = {"X-API-Key": agent["api_key"]}

            # First 2 requests should succeed (201)
            for _ in range(2):
                resp = await client.post(
                    "/tasks",
                    json={
                        "task_spec": {"type": "coding"},
                        "publisher_id": agent["id"],
                        "reward": 1.0,
                    },
                    headers=headers,
                )
                assert resp.status_code == 201

            # 3rd request should be rate-limited
            resp = await client.post(
                "/tasks",
                json={
                    "task_spec": {"type": "coding"},
                    "publisher_id": agent["id"],
                    "reward": 1.0,
                },
                headers=headers,
            )
            assert resp.status_code == 429
            assert "Retry-After" in resp.headers
            assert int(resp.headers["Retry-After"]) >= 1
        finally:
            # Restore permissive limiter
            from tests.conftest import _override_rate_limiter

            app.dependency_overrides[get_rate_limiter] = _override_rate_limiter

    @pytest.mark.asyncio
    async def test_public_endpoint_rate_limited(self, client):
        """Public endpoints should return 429 when limit exceeded."""
        from agentrelay.api.app import app
        from agentrelay.api.deps import get_rate_limiter

        strict = RateLimiter(max_requests=2, window_seconds=60)
        app.dependency_overrides[get_rate_limiter] = lambda: strict

        try:
            for _ in range(2):
                resp = await client.get("/tasks/available")
                assert resp.status_code == 200

            resp = await client.get("/tasks/available")
            assert resp.status_code == 429
            assert "Retry-After" in resp.headers
        finally:
            from tests.conftest import _override_rate_limiter

            app.dependency_overrides[get_rate_limiter] = _override_rate_limiter

    @pytest.mark.asyncio
    async def test_health_not_rate_limited(self, client):
        """Health endpoint should never be rate-limited."""
        from agentrelay.api.app import app
        from agentrelay.api.deps import get_rate_limiter

        strict = RateLimiter(max_requests=1, window_seconds=60)
        app.dependency_overrides[get_rate_limiter] = lambda: strict

        try:
            for _ in range(5):
                resp = await client.get("/health")
                assert resp.status_code == 200
        finally:
            from tests.conftest import _override_rate_limiter

            app.dependency_overrides[get_rate_limiter] = _override_rate_limiter
