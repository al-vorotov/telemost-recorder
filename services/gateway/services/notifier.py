import logging

from sqlalchemy.ext.asyncio import AsyncSession

from shared.db.models import SessionRecord, User
from shared.queues.session_queue import NotificationMessage, SessionQueue

logger = logging.getLogger(__name__)


async def notify_user(
    queue: SessionQueue,
    db: AsyncSession,
    record: SessionRecord,
    text: str,
    *,
    show_recording_controls: bool = False,
    show_transcribe_prompt: bool = False,
    show_audio_cleanup: bool = False,
    attach_transcript: bool = False,
) -> None:
    user = await db.get(User, record.user_id)
    if not user:
        return
    await queue.publish_notification(
        NotificationMessage(
            telegram_id=user.telegram_id,
            text=text,
            session_id=str(record.id),
            show_recording_controls=show_recording_controls,
            show_transcribe_prompt=show_transcribe_prompt,
            show_audio_cleanup=show_audio_cleanup,
            attach_transcript=attach_transcript,
        )
    )
    logger.debug("Notification → tg:%s session:%s", user.telegram_id, record.id)
