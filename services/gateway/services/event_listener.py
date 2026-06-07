import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from services.gateway.deps import get_session_factory, get_worker_manager
from services.gateway.services.session_fsm import InvalidTransitionError
from services.gateway.services.session_service import SessionService
from shared.config.settings import get_settings
from shared.contracts.session import SessionStatus
from shared.db.models import SessionRecord
from shared.queues.session_queue import SessionQueue

logger = logging.getLogger(__name__)

GATEWAY_GROUP = "gateway"
CONSUMER_NAME = "gateway-events"


async def run_event_listener() -> None:
    settings = get_settings()
    queue = SessionQueue(settings.redis_url)
    factory = get_session_factory()
    svc = SessionService(settings, session_factory=factory)
    worker_mgr = get_worker_manager()

    logger.info("Gateway event listener started")

    try:
        async for msg_id, event in queue.read_events(GATEWAY_GROUP, CONSUMER_NAME):
            try:
                sid = UUID(event.session_id)
                async with factory() as db:
                    record = await db.get(SessionRecord, sid)
                    if not record:
                        await queue.ack_event(GATEWAY_GROUP, msg_id)
                        continue

                    status = SessionStatus(record.status)

                    if event.event == "waiting_room" and status == SessionStatus.JOINING:
                        await svc._transition(db, record, "waiting_room")  # noqa: SLF001
                    elif event.event == "recording" and status in (
                        SessionStatus.JOINING,
                        SessionStatus.WAITING_ROOM,
                    ):
                        try:
                            await svc._transition(db, record, "recording")
                        except InvalidTransitionError:
                            if status == SessionStatus.JOINING:
                                await svc._transition(db, record, "waiting_room")
                                record = await db.get(SessionRecord, sid)
                                if record:
                                    await svc._transition(db, record, "recording")
                    elif event.event == "capture_stopped":
                        worker_mgr.notify_capture_stopped(record.id)
                    elif event.event == "left":
                        worker_mgr.notify_left(record.id)
                    elif event.event == "failed":
                        try:
                            record.error_code = (event.message or "worker_failed")[:64]
                            await svc._transition(db, record, "fail")
                        except InvalidTransitionError:
                            pass
                    elif event.event == "meeting_ended":
                        if status == SessionStatus.IN_CALL:
                            await svc._transition(db, record, "leave")
                    elif event.event == "transcribing":
                        if status == SessionStatus.TRANSCRIPTION_QUEUED:
                            await svc._transition(db, record, "transcribing")
                    elif event.event == "transcript_ready":
                        if event.transcript_path:
                            record.transcript_object_key = event.transcript_path
                        else:
                            record.transcript_object_key = str(
                                svc._storage.transcript_path(record.id)  # noqa: SLF001
                            )
                        record.transcribed_at = datetime.now(UTC)
                        await db.commit()
                        if status == SessionStatus.TRANSCRIBING:
                            await svc._transition(db, record, "transcript_ready")
                            record = await db.get(SessionRecord, sid)
                        if record and record.status == SessionStatus.TRANSCRIPT_READY.value:
                            await svc._transition(db, record, "await_audio_disposal")
                    elif event.event == "transcription_failed":
                        record.error_code = (event.message or "transcription_failed")[:64]
                        try:
                            await svc._transition(db, record, "fail")
                        except InvalidTransitionError:
                            pass

            except Exception:
                logger.exception("Failed to handle event %s", event)
            finally:
                await queue.ack_event(GATEWAY_GROUP, msg_id)
    except asyncio.CancelledError:
        logger.info("Event listener cancelled")
    finally:
        await queue.close()
