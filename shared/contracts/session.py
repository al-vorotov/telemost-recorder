from enum import StrEnum


class SessionStatus(StrEnum):
    """Жизненный цикл сессии записи (источник правды — gateway)."""

    SCHEDULED = "scheduled"
    QUEUED = "queued"
    JOINING = "joining"
    WAITING_ROOM = "waiting_room"
    RECORDING = "recording"
    CAPTURE_STOPPED = "capture_stopped"
    IN_CALL = "in_call"
    RECORDED = "recorded"
    TRANSCRIPTION_QUEUED = "transcription_queued"
    TRANSCRIBING = "transcribing"
    TRANSCRIPT_READY = "transcript_ready"
    PENDING_AUDIO_DISPOSAL = "pending_audio_disposal"
    COMPLETED = "completed"
    FAILED = "failed"
