"""Config smoke tests."""

from agentrelay.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings(DATABASE_URL="postgresql+asyncpg://x@localhost/test", REDIS_URL="redis://localhost", DEBUG=False)
        assert "asyncpg" in s.DATABASE_URL
        assert s.DEBUG is False

    def test_debug_flag(self):
        s = Settings(DATABASE_URL="postgresql+asyncpg://x@localhost/test", REDIS_URL="redis://localhost", DEBUG=True)
        assert s.DEBUG is True
