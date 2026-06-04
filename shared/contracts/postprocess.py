"""Задел под LLM-постобработку транскрипта (фаза 2+)."""

from typing import Protocol


class PostProcessor(Protocol):
    async def process(
        self,
        text: str,
        prompt_template_id: str,
        variables: dict[str, str] | None = None,
    ) -> str: ...
