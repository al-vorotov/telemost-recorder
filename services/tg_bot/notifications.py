import asyncio
import logging

from aiogram import Bot

from shared.config.settings import Settings
from shared.queues.session_queue import SessionQueue

logger = logging.getLogger(__name__)

TG_BOT_GROUP = "tg_bot"
CONSUMER_NAME = "tg-bot-notifications"


async def run_notification_listener(bot: Bot, settings: Settings) -> None:
    queue = SessionQueue(settings.redis_url)
    logger.info("Notification listener started")
    try:
        async for msg_id, notification in queue.read_notifications(TG_BOT_GROUP, CONSUMER_NAME):
            try:
                await bot.send_message(notification.telegram_id, notification.text)
            except Exception:
                logger.exception("Failed to send notification to %s", notification.telegram_id)
            finally:
                await queue.ack_notification(TG_BOT_GROUP, msg_id)
    except asyncio.CancelledError:
        logger.info("Notification listener stopped")
    finally:
        await queue.close()
