import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from services.gateway.deps import setup_app
from services.gateway.routers import sessions
from services.gateway.services.event_listener import run_event_listener


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await setup_app()
    listener_task = asyncio.create_task(run_event_listener())
    yield
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass


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
