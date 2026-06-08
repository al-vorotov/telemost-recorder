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
        "/status — текущая сессия"
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
