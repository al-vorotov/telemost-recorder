import asyncio
import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from services.tg_bot.clients.gateway import GatewayClient
from services.tg_bot.handlers.common import parse_schedule_datetime, parse_session_id, validate_link
from shared.config.settings import get_settings
from services.tg_bot.keyboards.session import (
    cancel_scheduled_keyboard,
    delete_audio_keyboard,
    in_call_keyboard,
    join_mode_keyboard,
    leave_keyboard,
    recording_keyboard,
    transcribe_keyboard,
)
from shared.contracts.session import SessionStatus

logger = logging.getLogger(__name__)
router = Router()

_pending_links: dict[int, str] = {}
_awaiting_schedule: set[int] = set()
_active_sessions: dict[int, UUID] = {}


def _format_status(data: dict) -> str:
    return f"Статус: {data['status_label']}"


async def _poll_until(
    gw: GatewayClient,
    session_id: UUID,
    telegram_id: int,
    target_statuses: set[str],
    *,
    timeout_sec: float = 120,
    interval_sec: float = 2,
) -> dict:
    elapsed = 0.0
    last = await gw.get_session(session_id, telegram_id)
    while last["status"] not in target_statuses and elapsed < timeout_sec:
        await asyncio.sleep(interval_sec)
        elapsed += interval_sec
        last = await gw.get_session(session_id, telegram_id)
    return last


@router.message(F.text)
async def on_text(message: Message, gateway: GatewayClient) -> None:
    if not message.from_user or not message.text:
        return

    if message.from_user.id in _awaiting_schedule:
        await _handle_schedule_datetime(message, gateway)
        return

    url = validate_link(message.text)
    if not url:
        await message.answer(
            "Не вижу ссылку на Телемост. Пришлите URL вида https://telemost.yandex.ru/j/..."
        )
        return

    _pending_links[message.from_user.id] = url
    await message.answer(
        f"Ссылка принята.\n{url}\n\nКак подключиться?",
        reply_markup=join_mode_keyboard(),
    )


@router.callback_query(F.data == "join_now")
async def on_join_now(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user:
        return

    url = _pending_links.pop(callback.from_user.id, None)
    if not url:
        await callback.answer("Сначала отправьте ссылку на встречу", show_alert=True)
        return

    await callback.answer()
    try:
        data = await gateway.create_session(
            meeting_url=url,
            telegram_id=callback.from_user.id,
            mode="now",
        )
    except Exception as e:
        logger.exception("create_session failed")
        await callback.message.answer(f"Не удалось создать сессию: {e}")  # type: ignore[union-attr]
        return

    session_id = UUID(data["id"])
    _active_sessions[callback.from_user.id] = session_id
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"Сессия создана.\n{_format_status(data)}",
    )

    data = await _poll_until(
        gateway,
        session_id,
        callback.from_user.id,
        {SessionStatus.RECORDING.value, SessionStatus.FAILED.value},
    )
    if data["status"] == SessionStatus.FAILED.value:
        await callback.message.answer("Ошибка подключения к звонку.")  # type: ignore[union-attr]
        return

    await callback.message.answer(  # type: ignore[union-attr]
        f"{_format_status(data)}\n\nМожно остановить запись.",
        reply_markup=recording_keyboard(session_id),
    )


@router.callback_query(F.data == "join_schedule")
async def on_join_schedule(callback: CallbackQuery) -> None:
    if not callback.from_user:
        return
    if callback.from_user.id not in _pending_links:
        await callback.answer("Сначала отправьте ссылку на встречу", show_alert=True)
        return
    _awaiting_schedule.add(callback.from_user.id)
    await callback.answer()
    await callback.message.answer(  # type: ignore[union-attr]
        "Введите дату и время подключения в формате:\n"
        "ДД.ММ.ГГГГ ЧЧ:ММ\n\n"
        "Например: 08.06.2026 14:30 (время Москвы)"
    )


async def _handle_schedule_datetime(message: Message, gateway: GatewayClient) -> None:
    if not message.from_user or not message.text:
        return
    settings = get_settings()
    scheduled_at = parse_schedule_datetime(message.text, settings.schedule_timezone)
    if not scheduled_at:
        await message.answer("Не понял формат. Пример: 08.06.2026 14:30")
        return

    _awaiting_schedule.discard(message.from_user.id)
    url = _pending_links.pop(message.from_user.id, None)
    if not url:
        await message.answer("Ссылка потерялась — пришлите её снова.")
        return

    try:
        data = await gateway.create_session(
            meeting_url=url,
            telegram_id=message.from_user.id,
            mode="scheduled",
            scheduled_at=scheduled_at,
        )
    except Exception as e:
        logger.exception("schedule create_session failed")
        await message.answer(f"Не удалось запланировать: {e}")
        return

    _active_sessions[message.from_user.id] = UUID(data["id"])
    session_id = UUID(data["id"])
    await message.answer(
        f"Запланировано на {scheduled_at.strftime('%d.%m.%Y %H:%M')} (МСК).\n"
        f"Статус: {data['status_label']}\n\n"
        "В назначенное время подключусь автоматически.\n"
        "/status — проверить · /cancel — отменить",
        reply_markup=cancel_scheduled_keyboard(session_id),
    )


@router.callback_query(F.data.startswith("cancel_scheduled:"))
async def on_cancel_scheduled(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user or not callback.data:
        return
    parsed = parse_session_id(callback.data)
    if not parsed:
        return
    _, session_id = parsed
    await callback.answer()
    try:
        data = await gateway.cancel_scheduled(session_id, callback.from_user.id)
    except Exception as e:
        await callback.message.answer(f"Не удалось отменить: {e}")  # type: ignore[union-attr]
        return
    _active_sessions.pop(callback.from_user.id, None)
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"Запланированная сессия отменена.\n{_format_status(data)}"
    )


@router.callback_query(F.data.startswith("confirm_summarize:"))
async def on_confirm_summarize(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user or not callback.data:
        return
    parsed = parse_session_id(callback.data)
    if not parsed:
        return
    _, session_id = parsed
    await callback.answer()
    await callback.message.answer("Готовлю краткое содержание…")  # type: ignore[union-attr]
    try:
        content = await gateway.summarize(session_id, callback.from_user.id)
        await callback.message.answer_document(  # type: ignore[union-attr]
            BufferedInputFile(content, filename="summary.md"),
            caption="Краткое содержание встречи.",
        )
    except Exception as e:
        await callback.message.answer(f"Не удалось: {e}")  # type: ignore[union-attr]


@router.callback_query(F.data.startswith("decline_summarize:"))
async def on_decline_summarize(callback: CallbackQuery) -> None:
    await callback.answer("Ок, без саммари")


@router.callback_query(F.data.startswith("stop_recording:"))
async def on_stop_recording(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user or not callback.data:
        return
    parsed = parse_session_id(callback.data)
    if not parsed:
        return
    _, session_id = parsed
    await callback.answer()
    data = await gateway.stop_recording(session_id, callback.from_user.id)
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"{_format_status(data)}\n\nОтключиться от звонка?",
        reply_markup=leave_keyboard(session_id),
    )


@router.callback_query(F.data.startswith("confirm_leave:"))
async def on_confirm_leave(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user or not callback.data:
        return
    parsed = parse_session_id(callback.data)
    if not parsed:
        return
    _, session_id = parsed
    await callback.answer()
    data = await gateway.leave(session_id, callback.from_user.id)
    await _ask_transcribe(callback, session_id, data)


@router.callback_query(F.data.startswith("decline_leave:"))
async def on_decline_leave(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user or not callback.data:
        return
    parsed = parse_session_id(callback.data)
    if not parsed:
        return
    _, session_id = parsed
    await callback.answer()
    data = await gateway.decline_leave(session_id, callback.from_user.id)
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"{_format_status(data)}\n\nБот остаётся в звонке без записи.",
        reply_markup=in_call_keyboard(session_id),
    )


@router.callback_query(F.data.startswith("leave_call:"))
async def on_leave_call(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user or not callback.data:
        return
    parsed = parse_session_id(callback.data)
    if not parsed:
        return
    _, session_id = parsed
    await callback.answer()
    data = await gateway.leave(session_id, callback.from_user.id)
    await _ask_transcribe(callback, session_id, data)


async def _ask_transcribe(callback: CallbackQuery, session_id: UUID, data: dict) -> None:
    await callback.message.edit_text(  # type: ignore[union-attr]
        f"{_format_status(data)}\n\nПодготовить транскрибацию?",
        reply_markup=transcribe_keyboard(session_id),
    )


@router.callback_query(F.data.startswith("confirm_transcribe:"))
async def on_confirm_transcribe(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user or not callback.data:
        return
    parsed = parse_session_id(callback.data)
    if not parsed:
        return
    _, session_id = parsed
    await callback.answer()
    data = await gateway.transcribe(session_id, callback.from_user.id)
    await callback.message.edit_text(_format_status(data))  # type: ignore[union-attr]

    data = await _poll_until(
        gateway,
        session_id,
        callback.from_user.id,
        {SessionStatus.PENDING_AUDIO_DISPOSAL.value, SessionStatus.FAILED.value},
        timeout_sec=300,
    )
    if data["status"] == SessionStatus.FAILED.value:
        await callback.message.answer("Ошибка транскрибации.")  # type: ignore[union-attr]
        return

    content = await gateway.download_transcript(session_id, callback.from_user.id)
    await callback.message.answer_document(  # type: ignore[union-attr]
        BufferedInputFile(content, filename="transcript.txt"),
        caption="Транскрипт готов.",
    )
    await _ask_delete_audio(callback, session_id)


@router.callback_query(F.data.startswith("decline_transcribe:"))
async def on_decline_transcribe(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user or not callback.data:
        return
    parsed = parse_session_id(callback.data)
    if not parsed:
        return
    _, session_id = parsed
    await callback.answer()
    await gateway.decline_transcribe(session_id, callback.from_user.id)
    await _ask_delete_audio(callback, session_id)


async def _ask_delete_audio(callback: CallbackQuery, session_id: UUID) -> None:
    await callback.message.answer(  # type: ignore[union-attr]
        "Удалить аудиозапись?",
        reply_markup=delete_audio_keyboard(session_id),
    )


@router.callback_query(F.data.startswith("delete_recording:"))
async def on_delete_recording(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user or not callback.data:
        return
    parsed = parse_session_id(callback.data)
    if not parsed:
        return
    _, session_id = parsed
    await callback.answer()
    data = await gateway.delete_recording(session_id, callback.from_user.id)
    _active_sessions.pop(callback.from_user.id, None)
    await callback.message.answer(f"Аудио удалено.\n{_format_status(data)}")  # type: ignore[union-attr]


@router.callback_query(F.data.startswith("keep_recording:"))
async def on_keep_recording(callback: CallbackQuery, gateway: GatewayClient) -> None:
    if not callback.from_user or not callback.data:
        return
    parsed = parse_session_id(callback.data)
    if not parsed:
        return
    _, session_id = parsed
    await callback.answer()
    data = await gateway.retain_audio(session_id, callback.from_user.id)
    _active_sessions.pop(callback.from_user.id, None)

    try:
        audio = await gateway.download_recording(session_id, callback.from_user.id)
        await callback.message.answer_document(  # type: ignore[union-attr]
            BufferedInputFile(audio, filename="recording.wav"),
            caption=(
                "Сохраните файл на компьютер. "
                "Если не удалите сами, аудио будет автоматически удалено через 7 дней."
            ),
        )
    except Exception:
        await callback.message.answer(  # type: ignore[union-attr]
            "Аудио сохранено на сервере. Скачивание недоступно (файл слишком большой или отсутствует)."
        )

    await callback.message.answer(_format_status(data))  # type: ignore[union-attr]
