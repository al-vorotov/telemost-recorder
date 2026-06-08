import asyncio
import logging

from aiogram import Bot, Dispatcher

from services.tg_bot.clients.gateway import GatewayClient
from services.tg_bot.handlers import setup_routers
from services.tg_bot.middleware import ACLMiddleware
from services.tg_bot.notifications import run_notification_listener
from shared.config.settings import get_settings

logger = logging.getLogger(__name__)


async def run_bot() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    gateway = GatewayClient(settings)

    dp.update.middleware(ACLMiddleware(settings))
    dp.include_router(setup_routers())

    @dp.update.middleware()
    async def inject_gateway(handler, event, data):  # type: ignore[no-untyped-def]
        data["gateway"] = gateway
        return await handler(event, data)

    notify_task = asyncio.create_task(run_notification_listener(bot, settings))
    logger.info("Starting Telegram bot")
    try:
        await dp.start_polling(bot)
    finally:
        notify_task.cancel()
        try:
            await notify_task
        except asyncio.CancelledError:
            pass
