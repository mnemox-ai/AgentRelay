"""Config smoke tests."""

from agentrelay.config import Settings


class TestSettings:
    def test_defaults(self):
        s = Settings(DATABASE_URL="postgresql+asyncpg://x@localhost/test", DEBUG=False)
        assert "asyncpg" in s.DATABASE_URL
        assert s.DEBUG is False
        assert s.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:5173"]
        assert s.APP_ENV == "development"
        assert s.SECRET_KEY == ""

    def test_debug_flag(self):
        s = Settings(DATABASE_URL="postgresql+asyncpg://x@localhost/test", DEBUG=True)
        assert s.DEBUG is True

    def test_custom_cors_origins(self):
        s = Settings(
            DATABASE_URL="postgresql+asyncpg://x@localhost/test",
            CORS_ORIGINS=["https://example.com"],
        )
        assert s.CORS_ORIGINS == ["https://example.com"]

    def test_custom_app_env(self):
        s = Settings(DATABASE_URL="postgresql+asyncpg://x@localhost/test", APP_ENV="production")
        assert s.APP_ENV == "production"
