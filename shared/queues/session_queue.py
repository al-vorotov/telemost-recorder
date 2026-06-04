import json
from dataclasses import asdict, dataclass
from typing import Any

import redis.asyncio as redis

COMMANDS_STREAM = "session.commands"
EVENTS_STREAM = "session.events"


@dataclass
class SessionCommand:
    session_id: str
    action: str  # STOP_CAPTURE | LEAVE

    def to_json(self) -> str:
        return json.dumps(asdict(self))


@dataclass
class SessionEvent:
    session_id: str
    event: str  # waiting_room | recording | capture_stopped | left | meeting_ended | failed
    message: str | None = None
    audio_path: str | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> "SessionEvent":
        return cls(
            session_id=data["session_id"],
            event=data["event"],
            message=data.get("message"),
            audio_path=data.get("audio_path"),
        )


class SessionQueue:
    def __init__(self, redis_url: str) -> None:
        self._redis = redis.from_url(redis_url, decode_responses=True)

    async def publish_command(self, cmd: SessionCommand) -> str:
        return await self._redis.xadd(COMMANDS_STREAM, {"payload": cmd.to_json()})

    async def publish_event(self, event: SessionEvent) -> str:
        return await self._redis.xadd(EVENTS_STREAM, {"payload": event.to_json()})

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

    async def close(self) -> None:
        await self._redis.aclose()
