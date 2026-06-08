import asyncio
import logging
from pathlib import Path

from shared.config.settings import Settings, get_settings
from shared.contracts.transcription import TranscriptionJob, TranscriptionResult

logger = logging.getLogger(__name__)


def _format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


class FasterWhisperBackend:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._model = None

    def _load_model(self):
        from faster_whisper import WhisperModel

        if self._model is None:
            logger.info(
                "Loading Whisper model=%s device=%s compute=%s",
                self._settings.whisper_model,
                self._settings.whisper_device,
                self._settings.whisper_compute_type,
            )
            self._model = WhisperModel(
                self._settings.whisper_model,
                device=self._settings.whisper_device,
                compute_type=self._settings.whisper_compute_type,
            )
        return self._model

    def _transcribe_sync(self, job: TranscriptionJob) -> TranscriptionResult:
        if not job.audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {job.audio_path}")

        model = self._load_model()
        segments, info = model.transcribe(
            str(job.audio_path),
            language=job.language,
            vad_filter=True,
        )

        lines: list[str] = []
        for segment in segments:
            text = segment.text.strip()
            if text:
                lines.append(f"[{_format_timestamp(segment.start)}] {text}")

        body = "\n".join(lines)
        if body:
            body += "\n"

        transcript_path = job.audio_path.parent / "transcript.txt"
        transcript_path.write_text(body, encoding="utf-8")

        duration = getattr(info, "duration", None)
        logger.info(
            "Transcribed session %s → %s (%s lines)",
            job.session_id,
            transcript_path,
            len(lines),
        )
        return TranscriptionResult(
            session_id=job.session_id,
            transcript_path=transcript_path,
            duration_sec=float(duration) if duration is not None else None,
        )

    async def transcribe(self, job: TranscriptionJob) -> TranscriptionResult:
        return await asyncio.to_thread(self._transcribe_sync, job)
