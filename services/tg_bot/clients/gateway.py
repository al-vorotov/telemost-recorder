import httpx

from shared.config.settings import Settings


class GatewayClient:
    def __init__(self, settings: Settings, base_url: str = "http://127.0.0.1:8000") -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-Api-Secret": settings.bot_api_secret}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=60.0)

    async def health(self) -> dict:
        async with self._client() as client:
            r = await client.get("/health")
            r.raise_for_status()
            return r.json()

    # TODO: create_session, stop_recording, leave, transcribe, delete_recording, retain_audio
