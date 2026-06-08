import logging
from pathlib import Path
from uuid import UUID

from services.transcriber.engine import FasterWhisperBackend
from shared.config.settings import Settings, get_settings
from shared.contracts.transcription import TranscriptionJob
from shared.queues.session_queue import SessionEvent, SessionQueue, TranscriptionJobMessage

logger = logging.getLogger(__name__)

TRANSCRIBER_GROUP = "transcribers"
CONSUMER_NAME = "transcriber-1"


class TranscriberRunner:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._queue = SessionQueue(self._settings.redis_url)
        self._backend = FasterWhisperBackend(self._settings)

    async def run(self) -> None:
        logger.info("Transcriber started, waiting for transcription.jobs")
        try:
            async for msg_id, job_msg in self._queue.read_transcription_jobs(
                TRANSCRIBER_GROUP, CONSUMER_NAME
            ):
                await self._process_job(job_msg)
                await self._queue.ack_transcription_job(TRANSCRIBER_GROUP, msg_id)
        finally:
            await self._queue.close()

    async def _process_job(self, job_msg: TranscriptionJobMessage) -> None:
        sid = job_msg.session_id
        transcript_path = Path(job_msg.audio_path).parent / "transcript.txt"
        if transcript_path.exists():
            logger.info("Transcript already exists for %s, skipping", sid)
            await self._queue.publish_event(
                SessionEvent(
                    sid,
                    "transcript_ready",
                    transcript_path=str(transcript_path),
                )
            )
            return

        await self._queue.publish_event(SessionEvent(sid, "transcribing"))

        job = TranscriptionJob(
            session_id=UUID(sid),
            audio_path=Path(job_msg.audio_path),
            language=job_msg.language,
            idempotency_key=job_msg.idempotency_key,
        )

        try:
            result = await self._backend.transcribe(job)
            await self._queue.publish_event(
                SessionEvent(
                    sid,
                    "transcript_ready",
                    transcript_path=str(result.transcript_path),
                )
            )
        except Exception as e:
            logger.exception("Transcription failed for %s", sid)
            await self._queue.publish_event(
                SessionEvent(sid, "transcription_failed", message=str(e)[:500])
            )
