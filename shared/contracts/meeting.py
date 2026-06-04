from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from uuid import UUID


class MeetingEventType(StrEnum):
    WAITING_ROOM = "waiting_room"
    RECORDING = "recording"
    MEETING_ENDED = "meeting_ended"
    KICKED = "kicked"
    ERROR = "error"


@dataclass(frozen=True)
class MeetingEvent:
    type: MeetingEventType
    message: str | None = None


@dataclass
class JoinContext:
    session_id: UUID
    meeting_url: str
    bot_display_name: str
    audio_output_path: Path


class AudioSink(Protocol):
    async def write_chunk(self, pcm: bytes) -> None: ...

    async def finalize(self) -> Path: ...


class MeetingProvider(Protocol):
    """Адаптер источника встреч (telemost, zoom, …)."""

    provider_id: str

    async def join(self, ctx: JoinContext) -> None: ...

    async def stop_capture(self, ctx: JoinContext) -> Path: ...

    async def leave(self, ctx: JoinContext) -> None: ...

    async def watch_events(self, ctx: JoinContext) -> AsyncIterator[MeetingEvent]: ...
