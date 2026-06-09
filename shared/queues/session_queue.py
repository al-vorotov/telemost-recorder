import json
from dataclasses import asdict, dataclass
from typing import Any

import redis.asyncio as redis

COMMANDS_STREAM = "session.commands"
EVENTS_STREAM = "session.events"
TRANSCRIPTION_JOBS_STREAM = "transcription.jobs"
NOTIFICATIONS_STREAM = "notifications"


@dataclass
class SessionCommand:
    session_id: str
    action: str  # STOP_CAPTURE | LEAVE

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class NotificationMessage:
    telegram_id: int
    text: str
    session_id: str | None = None
    # tg-bot: optional UI actions
    show_recording_controls: bool = False
    show_transcribe_prompt: bool = False
    show_audio_cleanup: bool = False
    attach_transcript: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "NotificationMessage":
        return cls(
            telegram_id=int(data["telegram_id"]),
            text=data["text"],
            session_id=data.get("session_id"),
            show_recording_controls=bool(data.get("show_recording_controls")),
            show_transcribe_prompt=bool(data.get("show_transcribe_prompt")),
            show_audio_cleanup=bool(data.get("show_audio_cleanup")),
            attach_transcript=bool(data.get("attach_transcript")),
        )


@dataclass
class TranscriptionJobMessage:
    session_id: str
    audio_path: str
    language: str = "ru"
    idempotency_key: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "TranscriptionJobMessage":
        return cls(
            session_id=data["session_id"],
            audio_path=data["audio_path"],
            language=data.get("language", "ru"),
            idempotency_key=data.get("idempotency_key"),
        )


@dataclass
class SessionEvent:
    session_id: str
    event: str
    message: str | None = None
    audio_path: str | None = None
    transcript_path: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "SessionEvent":
        return cls(
            session_id=data["session_id"],
            event=data["event"],
            message=data.get("message"),
            audio_path=data.get("audio_path"),
            transcript_path=data.get("transcript_path"),
        )


class SessionQueue:
    def __init__(self, redis_url: str) -> None:
        self._redis = redis.from_url(redis_url, decode_responses=True)

    async def publish_command(self, cmd: SessionCommand) -> str:
        return await self._redis.xadd(COMMANDS_STREAM, {"payload": cmd.to_json()})

    async def publish_event(self, event: SessionEvent) -> str:
        return await self._redis.xadd(EVENTS_STREAM, {"payload": event.to_json()})

    async def publish_transcription_job(self, job: TranscriptionJobMessage) -> str:
        return await self._redis.xadd(TRANSCRIPTION_JOBS_STREAM, {"payload": job.to_json()})

    async def publish_notification(self, notification: NotificationMessage) -> str:
        return await self._redis.xadd(NOTIFICATIONS_STREAM, {"payload": notification.to_json()})

    async def read_commands(
        self,
        consumer_group: str,
        consumer_name: str,
        *,
        block_ms: int = 5000,
    ):
        try:
            await self._redis.xgroup_create(COMMANDS_STREAM, consumer_group, id="0", mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        while True:
            messages = await self._redis.xreadgroup(
                consumer_group,
                consumer_name,
                {COMMANDS_STREAM: ">"},
                count=1,
                block=block_ms,
            )
            if not messages:
                continue
            for _stream, entries in messages:
                for msg_id, fields in entries:
                    payload = json.loads(fields["payload"])
                    cmd = SessionCommand(**payload)
                    yield msg_id, cmd

    async def ack_command(self, consumer_group: str, msg_id: str) -> None:
        await self._redis.xack(COMMANDS_STREAM, consumer_group, msg_id)

    async def read_events(
        self,
        consumer_group: str,
        consumer_name: str,
        *,
        block_ms: int = 5000,
    ):
        try:
            await self._redis.xgroup_create(EVENTS_STREAM, consumer_group, id="0", mkstream=True)
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        while True:
            messages = await self._redis.xreadgroup(
                consumer_group,
                consumer_name,
                {EVENTS_STREAM: ">"},
                count=10,
                block=block_ms,
            )
            if not messages:
                continue
            for _stream, entries in messages:
                for msg_id, fields in entries:
                    data = json.loads(fields["payload"])
                    yield msg_id, SessionEvent.from_payload(data)

    async def ack_event(self, consumer_group: str, msg_id: str) -> None:
        await self._redis.xack(EVENTS_STREAM, consumer_group, msg_id)

    async def read_transcription_jobs(
        self,
        consumer_group: str,
        consumer_name: str,
        *,
        block_ms: int = 5000,
    ):
        try:
            await self._redis.xgroup_create(
                TRANSCRIPTION_JOBS_STREAM, consumer_group, id="0", mkstream=True
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        while True:
            messages = await self._redis.xreadgroup(
                consumer_group,
                consumer_name,
                {TRANSCRIPTION_JOBS_STREAM: ">"},
                count=1,
                block=block_ms,
            )
            if not messages:
                continue
            for _stream, entries in messages:
                for msg_id, fields in entries:
                    data = json.loads(fields["payload"])
                    yield msg_id, TranscriptionJobMessage.from_payload(data)

    async def ack_transcription_job(self, consumer_group: str, msg_id: str) -> None:
        await self._redis.xack(TRANSCRIPTION_JOBS_STREAM, consumer_group, msg_id)

    async def read_notifications(
        self,
        consumer_group: str,
        consumer_name: str,
        *,
        block_ms: int = 5000,
    ):
        try:
            await self._redis.xgroup_create(
                NOTIFICATIONS_STREAM, consumer_group, id="0", mkstream=True
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        while True:
            messages = await self._redis.xreadgroup(
                consumer_group,
                consumer_name,
                {NOTIFICATIONS_STREAM: ">"},
                count=10,
                block=block_ms,
            )
            if not messages:
                continue
            for _stream, entries in messages:
                for msg_id, fields in entries:
                    data = json.loads(fields["payload"])
                    yield msg_id, NotificationMessage.from_payload(data)

    async def ack_notification(self, consumer_group: str, msg_id: str) -> None:
        await self._redis.xack(NOTIFICATIONS_STREAM, consumer_group, msg_id)

    async def close(self) -> None:
        await self._redis.aclose()
