import asyncio
import logging
from uuid import UUID

from aiogram import Bot
from aiogram.types import BufferedInputFile

from services.tg_bot.clients.gateway import GatewayClient
from services.tg_bot.keyboards.session import (
    delete_audio_keyboard,
    recording_keyboard,
    summarize_keyboard,
    transcribe_keyboard,
)
from shared.config.settings import Settings
from shared.queues.session_queue import SessionQueue

logger = logging.getLogger(__name__)

TG_BOT_GROUP = "tg_bot"
CONSUMER_NAME = "tg-bot-notifications"


async def run_notification_listener(bot: Bot, settings: Settings) -> None:
    queue = SessionQueue(settings.redis_url)
    gateway = GatewayClient(settings)
    logger.info("Notification listener started")
    try:
        async for msg_id, notification in queue.read_notifications(TG_BOT_GROUP, CONSUMER_NAME):
            try:
                await bot.send_message(notification.telegram_id, notification.text)

                if not notification.session_id:
                    continue

                sid = UUID(notification.session_id)

                if notification.attach_transcript:
                    try:
                        content = await gateway.download_transcript(sid, notification.telegram_id)
                        await bot.send_document(
                            notification.telegram_id,
                            BufferedInputFile(content, filename="transcript.txt"),
                        )
                    except Exception:
                        logger.exception("Failed to send transcript to %s", notification.telegram_id)

                if notification.show_recording_controls:
                    await bot.send_message(
                        notification.telegram_id,
                        "Управление записью:",
                        reply_markup=recording_keyboard(sid),
                    )
                if notification.show_summarize_prompt:
                    await bot.send_message(
                        notification.telegram_id,
                        "Сделать краткое содержание встречи (LLM)?",
                        reply_markup=summarize_keyboard(sid),
                    )
                if notification.show_transcribe_prompt:
                    await bot.send_message(
                        notification.telegram_id,
                        "Подготовить транскрибацию?",
                        reply_markup=transcribe_keyboard(sid),
                    )
                if notification.show_audio_cleanup:
                    await bot.send_message(
                        notification.telegram_id,
                        "Удалить аудиозапись?",
                        reply_markup=delete_audio_keyboard(sid),
                    )
            except Exception:
                logger.exception("Failed to send notification to %s", notification.telegram_id)
            finally:
                await queue.ack_notification(TG_BOT_GROUP, msg_id)
    except asyncio.CancelledError:
        logger.info("Notification listener stopped")
    finally:
        await queue.close()
