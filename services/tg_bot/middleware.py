from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from shared.config.settings import Settings


class ACLMiddleware(BaseMiddleware):
    def __init__(self, settings: Settings) -> None:
        self._allowed = settings.allowed_telegram_id_set

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not self._allowed:
            return await handler(event, data)

        user = data.get("event_from_user")
        if user is None or user.id not in self._allowed:
            if hasattr(event, "answer"):
                await event.answer("Нет доступа к боту", show_alert=True)
            elif hasattr(event, "reply"):
                await event.reply("Нет доступа к боту")
            return None
        return await handler(event, data)
