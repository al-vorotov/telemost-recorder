import logging

import httpx

from shared.config.settings import Settings

logger = logging.getLogger(__name__)


class LlmPostProcessor:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self._settings.llm_api_key.strip())

    async def summarize(self, transcript: str) -> str:
        if not self.enabled:
            raise RuntimeError("LLM is not configured (set LLM_API_KEY)")

        prompt = self._settings.llm_summary_prompt.format(transcript=transcript)
        url = f"{self._settings.llm_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._settings.llm_model,
            "messages": [
                {"role": "system", "content": "Ты помощник для конспектирования встреч."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as e:
            logger.error("Unexpected LLM response: %s", data)
            raise RuntimeError("Invalid LLM response") from e
