import logging

from aiogram import Bot, Dispatcher

from shared.config.settings import get_settings

logger = logging.getLogger(__name__)


async def run_bot() -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    # TODO: routers — start, session link, callbacks (stop, leave, transcribe, audio cleanup)

    @dp.message()
    async def echo_stub(message):  # type: ignore[no-untyped-def]
        await message.answer("telemost-recorder: бот в разработке. Отправьте ссылку на Телемост.")

    logger.info("Starting Telegram bot (stub)")
    await dp.start_polling(bot)
