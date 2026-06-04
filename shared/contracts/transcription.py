from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class TranscriptionJob:
    session_id: UUID
    audio_path: Path
    language: str = "ru"
    idempotency_key: str | None = None


@dataclass(frozen=True)
class TranscriptionResult:
    session_id: UUID
    transcript_path: Path
    duration_sec: float | None = None


class TranscriptionBackend(Protocol):
    async def transcribe(self, job: TranscriptionJob) -> TranscriptionResult: ...
