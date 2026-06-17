import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from services.gateway.deps import get_session_factory
from services.gateway.services.notifier import notify_user
from services.gateway.services.session_service import SessionService
from shared.config.settings import get_settings
from shared.contracts.session import SessionStatus
from shared.db.models import SessionRecord
from shared.queues.session_queue import SessionQueue

logger = logging.getLogger(__name__)


def _minutes_since(dt: datetime, now: datetime) -> float:
    return (now - dt).total_seconds() / 60.0


def _classify_followup_action(
    *,
    age_min: float,
    reminder_after: int,
    auto_after: int,
    interval: int,
) -> str | None:
    if age_min >= auto_after:
        return "auto"
    if reminder_after <= age_min < (reminder_after + interval):
        return "remind"
    return None


async def process_pending_audio_cleanup() -> tuple[int, int]:
    """
    Sends one reminder near configured threshold and auto-resolves stale sessions.
    Returns (reminded_count, auto_resolved_count).
    """
    settings = get_settings()
    reminder_after = settings.audio_cleanup_reminder_after_minutes
    auto_after = settings.audio_cleanup_auto_resolve_after_minutes
    interval = settings.audio_cleanup_followup_interval_minutes
    auto_action = settings.audio_cleanup_auto_action.strip().lower()
    if auto_action not in {"delete", "retain"}:
        auto_action = "delete"

    now = datetime.now(UTC)
    queue = SessionQueue(settings.redis_url)
    factory = get_session_factory()
    svc = SessionService(settings, session_factory=factory)
    reminded = 0
    auto_resolved = 0

    async with factory() as db:
        result = await db.execute(
            select(SessionRecord).where(
                SessionRecord.status == SessionStatus.PENDING_AUDIO_DISPOSAL.value,
                SessionRecord.audio_deleted_at.is_(None),
            )
        )
        records = result.scalars().all()

        for record in records:
            if not record.updated_at:
                continue
            age_min = _minutes_since(record.updated_at, now)

            action = _classify_followup_action(
                age_min=age_min,
                reminder_after=reminder_after,
                auto_after=auto_after,
                interval=interval,
            )

            if action == "auto":
                if auto_action == "delete":
                    await svc._storage.delete_audio(record.id)  # noqa: SLF001
                    record.audio_deleted_at = now
                    record = await svc._transition(db, record, "delete_audio")  # noqa: SLF001
                    text = (
                        "⏱️ Ответ не получен вовремя, поэтому аудио удалено автоматически "
                        "для завершения сессии."
                    )
                else:
                    record.audio_expires_at = now + timedelta(days=settings.audio_retention_days)
                    await db.commit()
                    await db.refresh(record)
                    record = await svc._transition(db, record, "retain_audio")  # noqa: SLF001
                    text = (
                        "⏱️ Ответ не получен вовремя, поэтому аудио оставлено автоматически. "
                        f"Удалю через {settings.audio_retention_days} дн."
                    )

                await notify_user(queue, db, record, text)
                auto_resolved += 1
                continue

            if action == "remind":
                await notify_user(
                    queue,
                    db,
                    record,
                    "Напомню: выберите, что делать с аудио записи.",
                    show_audio_cleanup=True,
                )
                reminded += 1

    await queue.close()
    if reminded or auto_resolved:
        logger.info(
            "Audio cleanup followup: reminded=%d auto_resolved=%d",
            reminded,
            auto_resolved,
        )
    return reminded, auto_resolved
