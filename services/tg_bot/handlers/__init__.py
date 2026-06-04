from aiogram import Router

from services.tg_bot.handlers.session_flow import router as session_router
from services.tg_bot.handlers.start import router as start_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(start_router)
    root.include_router(session_router)
    return root
