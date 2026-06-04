from datetime import datetime
from uuid import UUID

import httpx

from shared.config.settings import Settings


class GatewayClient:
    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.gateway_base_url.rstrip("/")
        self._headers = {"X-Api-Secret": settings.bot_api_secret}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=120.0)

    async def health(self) -> dict:
        async with self._client() as client:
            r = await client.get("/health")
            r.raise_for_status()
            return r.json()

    async def create_session(
        self,
        *,
        meeting_url: str,
        telegram_id: int,
        mode: str,
        scheduled_at: datetime | None = None,
    ) -> dict:
        async with self._client() as client:
            r = await client.post(
                "/sessions",
                json={
                    "meeting_url": meeting_url,
                    "telegram_id": telegram_id,
                    "mode": mode,
                    "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
                },
            )
            r.raise_for_status()
            return r.json()

    async def get_session(self, session_id: UUID, telegram_id: int) -> dict:
        async with self._client() as client:
            r = await client.get(f"/sessions/{session_id}", params={"telegram_id": telegram_id})
            r.raise_for_status()
            return r.json()

    async def stop_recording(self, session_id: UUID, telegram_id: int) -> dict:
        async with self._client() as client:
            r = await client.post(
                f"/sessions/{session_id}/stop-recording",
                params={"telegram_id": telegram_id},
            )
            r.raise_for_status()
            return r.json()

    async def leave(self, session_id: UUID, telegram_id: int) -> dict:
        async with self._client() as client:
            r = await client.post(
                f"/sessions/{session_id}/leave",
                params={"telegram_id": telegram_id},
            )
            r.raise_for_status()
            return r.json()

    async def decline_leave(self, session_id: UUID, telegram_id: int) -> dict:
        async with self._client() as client:
            r = await client.post(
                f"/sessions/{session_id}/decline-leave",
                params={"telegram_id": telegram_id},
            )
            r.raise_for_status()
            return r.json()

    async def transcribe(self, session_id: UUID, telegram_id: int) -> dict:
        async with self._client() as client:
            r = await client.post(
                f"/sessions/{session_id}/transcribe",
                params={"telegram_id": telegram_id},
            )
            r.raise_for_status()
            return r.json()

    async def decline_transcribe(self, session_id: UUID, telegram_id: int) -> dict:
        async with self._client() as client:
            r = await client.post(
                f"/sessions/{session_id}/decline-transcribe",
                params={"telegram_id": telegram_id},
            )
            r.raise_for_status()
            return r.json()

    async def delete_recording(self, session_id: UUID, telegram_id: int) -> dict:
        async with self._client() as client:
            r = await client.delete(
                f"/sessions/{session_id}/recording",
                params={"telegram_id": telegram_id},
            )
            r.raise_for_status()
            return r.json()

    async def retain_audio(self, session_id: UUID, telegram_id: int) -> dict:
        async with self._client() as client:
            r = await client.post(
                f"/sessions/{session_id}/retain-audio",
                params={"telegram_id": telegram_id},
            )
            r.raise_for_status()
            return r.json()

    async def download_transcript(self, session_id: UUID, telegram_id: int) -> bytes:
        async with self._client() as client:
            r = await client.get(
                f"/sessions/{session_id}/transcript",
                params={"telegram_id": telegram_id},
            )
            r.raise_for_status()
            return r.content

    async def download_recording(self, session_id: UUID, telegram_id: int) -> bytes:
        async with self._client() as client:
            r = await client.get(
                f"/sessions/{session_id}/recording/download",
                params={"telegram_id": telegram_id},
            )
            r.raise_for_status()
            return r.content
