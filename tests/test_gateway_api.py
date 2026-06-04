from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from services.gateway.app import create_app
from services.gateway.deps import get_session_factory, reset_session_factory
from services.gateway.services.session_service import SessionService
from shared.config.settings import get_settings
from shared.contracts.session import SessionStatus
from shared.db.models import SessionRecord


@pytest.fixture
async def client(tmp_path, monkeypatch):
    pytest.importorskip("aiosqlite")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("BOT_API_SECRET", "test-secret")
    monkeypatch.setenv("ALLOWED_TELEGRAM_IDS", "42")
    monkeypatch.setenv("SIMULATE_MEETING", "false")
    reset_session_factory()
    get_settings.cache_clear()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    reset_session_factory()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_session_lifecycle(client: AsyncClient) -> None:
    headers = {"X-Api-Secret": "test-secret"}
    url = "https://telemost.yandex.ru/j/12345678901234"

    r = await client.post(
        "/sessions",
        json={"meeting_url": url, "telegram_id": 42, "mode": "now"},
        headers=headers,
    )
    assert r.status_code == 200
    sid = r.json()["id"]

    factory = get_session_factory()
    async with factory() as db:
        record = await db.get(SessionRecord, UUID(sid))
        record.status = SessionStatus.RECORDING.value
        await db.commit()

    r = await client.post(f"/sessions/{sid}/stop-recording", params={"telegram_id": 42}, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "capture_stopped"

    r = await client.post(f"/sessions/{sid}/leave", params={"telegram_id": 42}, headers=headers)
    assert r.json()["status"] == "recorded"

    r = await client.post(f"/sessions/{sid}/decline-transcribe", params={"telegram_id": 42}, headers=headers)
    assert r.json()["status"] == "pending_audio_disposal"

    r = await client.delete(f"/sessions/{sid}/recording", params={"telegram_id": 42}, headers=headers)
    assert r.json()["status"] == "completed"
