import logging
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from services.gateway.db import create_session_factory
from services.gateway.services.session_service import SessionService
from shared.config.settings import Settings, get_settings
from shared.contracts.session import SessionStatus
from shared.db.models import SessionRecord, User
from shared.queues.session_queue import NotificationMessage, SessionQueue

logger = logging.getLogger(__name__)


class SessionScheduler:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._scheduler = AsyncIOScheduler(timezone=ZoneInfo(self._settings.schedule_timezone))
        self._factory = create_session_factory(self._settings)
        self._queue = SessionQueue(self._settings.redis_url)

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("Session scheduler started (tz=%s)", self._settings.schedule_timezone)

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    async def restore_pending(self) -> None:
        async with self._factory() as db:
            result = await db.execute(
                select(SessionRecord).where(SessionRecord.status == SessionStatus.SCHEDULED.value)
            )
            records = result.scalars().all()
            for record in records:
                if record.scheduled_at:
                    self.schedule_join(record.id, record.scheduled_at)
        logger.info("Restored %d scheduled sessions", len(records))

    def schedule_join(self, session_id: UUID, run_at: datetime) -> None:
        if run_at.tzinfo is None:
            run_at = run_at.replace(tzinfo=ZoneInfo(self._settings.schedule_timezone))
        run_at_utc = run_at.astimezone(UTC)
        job_id = f"join-{session_id}"

        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        if run_at_utc <= datetime.now(UTC):
            self._scheduler.add_job(
                self._fire_join,
                "date",
                run_date=datetime.now(UTC),
                args=[session_id],
                id=job_id,
                replace_existing=True,
            )
        else:
            self._scheduler.add_job(
                self._fire_join,
                "date",
                run_date=run_at_utc,
                args=[session_id],
                id=job_id,
                replace_existing=True,
            )
        logger.info("Scheduled join for %s at %s", session_id, run_at_utc.isoformat())

    async def _fire_join(self, session_id: UUID) -> None:
        from services.gateway.deps import get_worker_manager

        svc = SessionService(
            self._settings,
            session_factory=self._factory,
            worker_manager=get_worker_manager(),
        )
        telegram_id: int | None = None

        async with self._factory() as db:
            record = await db.get(SessionRecord, session_id)
            if not record or record.status != SessionStatus.SCHEDULED.value:
                logger.warning("Skip scheduled join for %s (status=%s)", session_id, getattr(record, "status", None))
                return

            user = await db.get(User, record.user_id)
            telegram_id = user.telegram_id if user else None

            await svc._transition(db, record, "start_join")  # noqa: SLF001
            await db.refresh(record)

            if self._settings.simulate_meeting:
                svc._schedule_simulate_join(session_id)  # noqa: SLF001
            else:
                get_worker_manager().spawn(session_id)

        if telegram_id:
            await self._queue.publish_notification(
                NotificationMessage(
                    telegram_id=telegram_id,
                    text="⏰ Время подключения — захожу в звонок…",
                    session_id=str(session_id),
                )
            )
