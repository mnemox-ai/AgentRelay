"""Shared test fixtures — async SQLite test database."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from agentrelay.models.base import Base
from agentrelay.api.app import app
from agentrelay.api.deps import get_db, get_rate_limiter
from agentrelay.security.rate_limiter import RateLimiter

# --------------------------------------------------------------------------
# Make PostgreSQL types work on SQLite
# --------------------------------------------------------------------------

# JSONB → JSON
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


# PostgreSQL UUID → CHAR(32)
@compiles(UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"


# --------------------------------------------------------------------------
# Test engine & session — StaticPool forces a single connection for SQLite
# --------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite://"

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=StaticPool,
)
TestSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db():
    async with TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db

# Use a very permissive rate limiter for tests so existing tests are not blocked
_test_rate_limiter = RateLimiter(max_requests=10_000, window_seconds=1)


def _override_rate_limiter() -> RateLimiter:
    return _test_rate_limiter


app.dependency_overrides[get_rate_limiter] = _override_rate_limiter


# --------------------------------------------------------------------------
# Mock Redis — tests should never touch a real Redis instance
# --------------------------------------------------------------------------

async def _mock_get_redis():
    raise ConnectionError("Redis disabled in tests")


@pytest.fixture(autouse=True)
def _disable_redis():
    """Prevent tests from connecting to a real Redis instance."""
    with patch("agentrelay.api.routes.tasks.get_redis", _mock_get_redis):
        yield


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    """Provide a DB session for verifying side effects in integration tests."""
    async with TestSessionFactory() as session:
        yield session
