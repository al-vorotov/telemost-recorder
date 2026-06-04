from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.gateway.deps import setup_app
from services.gateway.routers import sessions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await setup_app()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="telemost-recorder gateway",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(sessions.router)

    return app
