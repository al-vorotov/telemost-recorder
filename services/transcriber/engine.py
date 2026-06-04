"""Обёртка faster-whisper (логика из faster_whisper_cli — следующий этап)."""

from shared.contracts.transcription import TranscriptionJob, TranscriptionResult


class FasterWhisperBackend:
    def __init__(self) -> None:
        self._model = None  # lazy load WhisperModel

    async def transcribe(self, job: TranscriptionJob) -> TranscriptionResult:
        raise NotImplementedError("Whisper transcribe — в разработке")
