from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from services.tg_bot.clients.gateway import GatewayClient
from services.tg_bot.keyboards.session import recording_keyboard
from shared.contracts.session import SessionStatus

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я записываю звонки в Яндекс Телемост.\n\n"
        "Отправьте ссылку на встречу, например:\n"
        "https://telemost.yandex.ru/j/12345678901234\n\n"
        "/status — текущая сессия\n"
        "/cancel — отменить запланированное подключение"
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, gateway: GatewayClient) -> None:
    if not message.from_user:
        return
    data = await gateway.get_active_session(message.from_user.id)
    if not data:
        await message.answer("Нет активной сессии для отмены.")
        return
    if data["status"] != SessionStatus.SCHEDULED.value:
        await message.answer("Отменить можно только запланированную сессию. Текущий статус: " + data["status_label"])
        return
    from uuid import UUID

    from services.tg_bot.keyboards.session import cancel_scheduled_keyboard

    sid = UUID(data["id"])
    await message.answer(
        f"Отменить подключение на {data.get('scheduled_at', '?')}?",
        reply_markup=cancel_scheduled_keyboard(sid),
    )


@router.message(Command("status"))
async def cmd_status(message: Message, gateway: GatewayClient) -> None:
    if not message.from_user:
        return
    data = await gateway.get_active_session(message.from_user.id)
    if not data:
        await message.answer("Активных сессий нет.")
        return
    text = (
        f"Сессия: {data['id']}\n"
        f"{data['status_label']}\n"
        f"Ссылка: {data['meeting_url']}"
    )
    if data.get("scheduled_at"):
        text += f"\nЗапланировано: {data['scheduled_at']}"
    await message.answer(text)
    if data["status"] == SessionStatus.RECORDING.value:
        from uuid import UUID

        await message.answer(
            "Можно остановить запись.",
            reply_markup=recording_keyboard(UUID(data["id"])),
        )
