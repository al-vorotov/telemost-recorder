from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я записываю звонки в Яндекс Телемост.\n\n"
        "Отправьте ссылку на встречу, например:\n"
        "https://telemost.yandex.ru/j/12345678901234"
    )
