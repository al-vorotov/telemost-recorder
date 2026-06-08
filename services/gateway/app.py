import asyncio
from contextlib import asynccontextmanager

from apscheduler.triggers.interval import IntervalTrigger
from fastapi import FastAPI

from services.gateway.deps import get_scheduler, setup_app
from services.gateway.routers import sessions
from services.gateway.services.event_listener import run_event_listener
from services.gateway.services.retention_sweeper import sweep_expired_audio
from shared.config.settings import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    await setup_app()

    scheduler = get_scheduler()
    scheduler.start()
    await scheduler.restore_pending()

    retention_job = scheduler._scheduler.add_job(  # noqa: SLF001
        sweep_expired_audio,
        IntervalTrigger(hours=settings.retention_sweep_interval_hours),
        id="retention-sweep",
        replace_existing=True,
    )

    listener_task = asyncio.create_task(run_event_listener())
    yield

    listener_task.cancel()
    retention_job.remove()
    scheduler.shutdown()
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
