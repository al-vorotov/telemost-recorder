import asyncio
import logging
from uuid import UUID

from providers.registry import get_provider
from providers.telemost.provider import TelemostProvider
from shared.config.settings import Settings, get_settings
from shared.contracts.meeting import JoinContext, MeetingEventType
from shared.contracts.session import SessionStatus
from shared.db.models import SessionRecord
from shared.queues.session_queue import SessionCommand, SessionEvent, SessionQueue
from shared.storage.local import LocalStorageAdapter

logger = logging.getLogger(__name__)

GATEWAY_GROUP = "gateway"
WORKER_GROUP = "meeting_workers"


class MeetingWorkerRunner:
    def __init__(self, session_id: UUID, settings: Settings | None = None) -> None:
        self._session_id = session_id
        self._settings = settings or get_settings()
        self._storage = LocalStorageAdapter(self._settings)
        self._queue = SessionQueue(self._settings.redis_url)
        self._provider: TelemostProvider | None = None
        self._watch_task: asyncio.Task | None = None
        self._running = True

    async def run(self) -> None:
        from services.gateway.db import create_session_factory

        factory = create_session_factory(self._settings)
        async with factory() as db:
            record = await db.get(SessionRecord, self._session_id)
            if not record:
                logger.error("Session %s not found", self._session_id)
                await self._queue.publish_event(
                    SessionEvent(
                        str(self._session_id),
                        "failed",
                        message="session_not_found",
                    )
                )
                return
            meeting_url = record.meeting_url
            provider_id = record.provider
            bot_name = record.bot_display_name

        provider = get_provider(provider_id)
        if not isinstance(provider, TelemostProvider):
            await self._queue.publish_event(
                SessionEvent(str(self._session_id), "failed", message="unsupported_provider")
            )
            return

        self._provider = provider
        ctx = JoinContext(
            session_id=self._session_id,
            meeting_url=meeting_url,
            bot_display_name=bot_name,
            audio_output_path=self._storage.audio_path(self._session_id),
        )

        self._watch_task = asyncio.create_task(self._watch_events(ctx))

        try:
            await provider.join(ctx)
            await self._queue.publish_event(SessionEvent(str(self._session_id), "recording"))
        except Exception as e:
            logger.exception("Join failed")
            await self._queue.publish_event(
                SessionEvent(str(self._session_id), "failed", message=str(e))
            )
            await provider.close()
            return

        consumer_name = f"worker-{self._session_id}"
        try:
            async for msg_id, cmd in self._queue.read_commands(WORKER_GROUP, consumer_name):
                if cmd.session_id != str(self._session_id):
                    await self._queue.ack_command(WORKER_GROUP, msg_id)
                    continue
                await self._handle_command(cmd, ctx)
                await self._queue.ack_command(WORKER_GROUP, msg_id)
                if cmd.action == "LEAVE":
                    break
        finally:
            self._running = False
            if self._watch_task:
                self._watch_task.cancel()
            await provider.close()
            await self._queue.close()

    async def _handle_command(self, cmd: SessionCommand, ctx: JoinContext) -> None:
        assert self._provider
        if cmd.action == "STOP_CAPTURE":
            path = await self._provider.stop_capture(ctx)
            await self._queue.publish_event(
                SessionEvent(
                    str(self._session_id),
                    "capture_stopped",
                    audio_path=str(path),
                )
            )
        elif cmd.action == "LEAVE":
            await self._provider.leave(ctx)
            await self._queue.publish_event(SessionEvent(str(self._session_id), "left"))
        else:
            logger.warning("Unknown command %s", cmd.action)

    async def _watch_events(self, ctx: JoinContext) -> None:
        assert self._provider
        try:
            async for event in self._provider.watch_events(ctx):
                if not self._running:
                    break
                if event.type == MeetingEventType.WAITING_ROOM:
                    await self._queue.publish_event(
                        SessionEvent(str(self._session_id), "waiting_room", event.message)
                    )
                elif event.type == MeetingEventType.RECORDING:
                    await self._queue.publish_event(
                        SessionEvent(str(self._session_id), "recording", event.message)
                    )
                elif event.type == MeetingEventType.MEETING_ENDED:
                    await self._queue.publish_event(
                        SessionEvent(str(self._session_id), "meeting_ended", event.message)
                    )
                    break
                elif event.type == MeetingEventType.ERROR:
                    await self._queue.publish_event(
                        SessionEvent(str(self._session_id), "failed", event.message)
                    )
                    break
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("watch_events error")
            await self._queue.publish_event(
                SessionEvent(str(self._session_id), "failed", message=str(e))
            )
