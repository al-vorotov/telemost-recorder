import logging
from datetime import UTC, datetime

from sqlalchemy import select

from services.gateway.deps import get_session_factory
from shared.config.settings import get_settings
from shared.db.models import SessionRecord
from shared.storage.local import LocalStorageAdapter

logger = logging.getLogger(__name__)


async def sweep_expired_audio() -> int:
    """Удаляет аудио, у которых истёк audio_expires_at."""
    settings = get_settings()
    factory = get_session_factory()
    storage = LocalStorageAdapter(settings)
    now = datetime.now(UTC)
    deleted = 0

    async with factory() as db:
        result = await db.execute(
            select(SessionRecord).where(
                SessionRecord.audio_expires_at.isnot(None),
                SessionRecord.audio_expires_at < now,
                SessionRecord.audio_deleted_at.is_(None),
            )
        )
        records = result.scalars().all()
        for record in records:
            path = storage.audio_path(record.id)
            if path.exists():
                await storage.delete_audio(record.id)
                deleted += 1
            record.audio_deleted_at = now
            logger.info("Retention sweep: deleted audio for session %s", record.id)
        if records:
            await db.commit()

    return deleted
