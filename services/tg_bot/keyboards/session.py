from uuid import UUID

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def _cb(action: str, session_id: UUID) -> str:
    return f"{action}:{session_id}"


def join_mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Подключиться сейчас", callback_data="join_now")],
            [InlineKeyboardButton(text="Запланировать", callback_data="join_schedule")],
        ]
    )


def recording_keyboard(session_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Остановить запись",
                    callback_data=_cb("stop_recording", session_id),
                )
            ],
        ]
    )


def leave_keyboard(session_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, отключиться", callback_data=_cb("confirm_leave", session_id)),
                InlineKeyboardButton(text="Нет, остаться", callback_data=_cb("decline_leave", session_id)),
            ],
        ]
    )


def in_call_keyboard(session_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отключиться от звонка",
                    callback_data=_cb("leave_call", session_id),
                )
            ],
        ]
    )


def transcribe_keyboard(session_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, транскрибировать",
                    callback_data=_cb("confirm_transcribe", session_id),
                ),
                InlineKeyboardButton(
                    text="Нет",
                    callback_data=_cb("decline_transcribe", session_id),
                ),
            ],
        ]
    )


def cancel_scheduled_keyboard(session_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отменить запланированное",
                    callback_data=_cb("cancel_scheduled", session_id),
                )
            ],
        ]
    )


def summarize_keyboard(session_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, краткое содержание",
                    callback_data=_cb("confirm_summarize", session_id),
                ),
                InlineKeyboardButton(
                    text="Нет",
                    callback_data=_cb("decline_summarize", session_id),
                ),
            ],
        ]
    )


def delete_audio_keyboard(session_id: UUID) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, удалить аудио",
                    callback_data=_cb("delete_recording", session_id),
                ),
                InlineKeyboardButton(
                    text="Нет, оставить (7 дней)",
                    callback_data=_cb("keep_recording", session_id),
                ),
            ],
        ]
    )
