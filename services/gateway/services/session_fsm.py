from shared.contracts.session import SessionStatus

# action -> (from_statuses, to_status)
_TRANSITIONS: dict[str, tuple[frozenset[SessionStatus], SessionStatus]] = {
    "schedule": (frozenset({SessionStatus.QUEUED}), SessionStatus.SCHEDULED),
    "start_join": (
        frozenset({SessionStatus.QUEUED, SessionStatus.SCHEDULED}),
        SessionStatus.JOINING,
    ),
    "waiting_room": (
        frozenset({SessionStatus.JOINING}),
        SessionStatus.WAITING_ROOM,
    ),
    "recording": (
        frozenset({SessionStatus.JOINING, SessionStatus.WAITING_ROOM}),
        SessionStatus.RECORDING,
    ),
    "stop_recording": (frozenset({SessionStatus.RECORDING}), SessionStatus.CAPTURE_STOPPED),
    "decline_leave": (frozenset({SessionStatus.CAPTURE_STOPPED}), SessionStatus.IN_CALL),
    "leave": (
        frozenset({SessionStatus.CAPTURE_STOPPED, SessionStatus.IN_CALL}),
        SessionStatus.RECORDED,
    ),
    "confirm_transcribe": (frozenset({SessionStatus.RECORDED}), SessionStatus.TRANSCRIPTION_QUEUED),
    "decline_transcribe": (
        frozenset({SessionStatus.RECORDED}),
        SessionStatus.PENDING_AUDIO_DISPOSAL,
    ),
    "transcribing": (
        frozenset({SessionStatus.TRANSCRIPTION_QUEUED}),
        SessionStatus.TRANSCRIBING,
    ),
    "transcript_ready": (frozenset({SessionStatus.TRANSCRIBING}), SessionStatus.TRANSCRIPT_READY),
    "await_audio_disposal": (
        frozenset({SessionStatus.TRANSCRIPT_READY}),
        SessionStatus.PENDING_AUDIO_DISPOSAL,
    ),
    "delete_audio": (
        frozenset({SessionStatus.PENDING_AUDIO_DISPOSAL}),
        SessionStatus.COMPLETED,
    ),
    "retain_audio": (
        frozenset({SessionStatus.PENDING_AUDIO_DISPOSAL}),
        SessionStatus.COMPLETED,
    ),
    "fail": (
        frozenset(
            {
                SessionStatus.QUEUED,
                SessionStatus.SCHEDULED,
                SessionStatus.JOINING,
                SessionStatus.WAITING_ROOM,
                SessionStatus.RECORDING,
                SessionStatus.CAPTURE_STOPPED,
                SessionStatus.IN_CALL,
                SessionStatus.TRANSCRIPTION_QUEUED,
                SessionStatus.TRANSCRIBING,
            }
        ),
        SessionStatus.FAILED,
    ),
}


class InvalidTransitionError(Exception):
    def __init__(self, current: SessionStatus, action: str) -> None:
        super().__init__(f"Cannot apply '{action}' from status '{current}'")
        self.current = current
        self.action = action


def apply_transition(current: SessionStatus, action: str) -> SessionStatus:
    rule = _TRANSITIONS.get(action)
    if rule is None:
        raise InvalidTransitionError(current, action)
    allowed_from, new_status = rule
    if current not in allowed_from:
        raise InvalidTransitionError(current, action)
    return new_status


def status_label(status: SessionStatus) -> str:
    labels = {
        SessionStatus.SCHEDULED: "Запланировано",
        SessionStatus.QUEUED: "В очереди",
        SessionStatus.JOINING: "Подключаюсь к звонку…",
        SessionStatus.WAITING_ROOM: "Зал ожидания — допустите бота вручную",
        SessionStatus.RECORDING: "Идёт запись",
        SessionStatus.CAPTURE_STOPPED: "Запись остановлена",
        SessionStatus.IN_CALL: "В звонке без записи",
        SessionStatus.RECORDED: "Вышел из звонка, запись сохранена",
        SessionStatus.TRANSCRIPTION_QUEUED: "Транскрибация в очереди",
        SessionStatus.TRANSCRIBING: "Транскрибирую…",
        SessionStatus.TRANSCRIPT_READY: "Транскрипт готов",
        SessionStatus.PENDING_AUDIO_DISPOSAL: "Решите, что делать с аудио",
        SessionStatus.COMPLETED: "Завершено",
        SessionStatus.FAILED: "Ошибка",
    }
    return labels.get(status, status.value)
