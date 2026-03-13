"""FastAPI application factory and entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agentrelay.api.routes import agents, health, tasks, validation
from agentrelay.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="Agent Relay", version="0.1.0")

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
