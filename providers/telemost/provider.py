from collections.abc import AsyncIterator
from pathlib import Path

from shared.contracts.meeting import JoinContext, MeetingEvent, MeetingEventType


class TelemostProvider:
    """Playwright-адаптер Яндекс Телемост (реализация — следующий этап)."""

    provider_id = "telemost"

    async def join(self, ctx: JoinContext) -> None:
        raise NotImplementedError("Telemost join — в разработке")

    async def stop_capture(self, ctx: JoinContext) -> Path:
        raise NotImplementedError("Telemost stop_capture — в разработке")

    async def leave(self, ctx: JoinContext) -> None:
        raise NotImplementedError("Telemost leave — в разработке")

    async def watch_events(self, ctx: JoinContext) -> AsyncIterator[MeetingEvent]:
        raise NotImplementedError("Telemost watch_events — в разработке")
        yield MeetingEvent(type=MeetingEventType.ERROR)  # pragma: no cover
