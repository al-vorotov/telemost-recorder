from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from services.gateway.db import create_session_factory, init_db
from services.gateway.services.session_service import SessionService
from shared.config.settings import Settings, get_settings

_session_factory: async_sessionmaker[AsyncSession] | None = None


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory()
    return _session_factory


def get_session_service() -> SessionService:
    return SessionService(get_settings(), session_factory=get_session_factory())


async def setup_app(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    await init_db(s)


def reset_session_factory() -> None:
    """For tests."""
    global _session_factory
    _session_factory = None
    get_session_factory.cache_clear()
