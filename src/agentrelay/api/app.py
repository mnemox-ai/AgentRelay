"""FastAPI application factory and entrypoint."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentrelay.api.routes import agents, health, tasks, validation
from agentrelay.config import settings
from agentrelay.db import async_session_factory
from agentrelay.services.expiration_service import expire_overdue_tasks

logger = logging.getLogger(__name__)

EXPIRATION_INTERVAL_SECONDS = 60


async def _expiration_loop() -> None:
    """Background loop that expires overdue tasks every EXPIRATION_INTERVAL_SECONDS."""
    while True:
        try:
            async with async_session_factory() as session:
                expired = await expire_overdue_tasks(session)
                await session.commit()
                if expired:
                    logger.info("Background expiration: expired %d tasks", len(expired))
        except Exception:
            logger.exception("Error in expiration background loop")
        await asyncio.sleep(EXPIRATION_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_expiration_loop())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def create_app() -> FastAPI:
    app = FastAPI(title="Agent Relay", version="0.2.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(agents.router)
    app.include_router(tasks.router)
    app.include_router(validation.router)

    return app


app = create_app()


def main():
    import uvicorn

    uvicorn.run("agentrelay.api.app:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
