import pytest

from services.gateway.services.session_fsm import InvalidTransitionError, apply_transition
from shared.contracts.session import SessionStatus


def test_stop_recording_from_recording() -> None:
    assert apply_transition(SessionStatus.RECORDING, "stop_recording") == SessionStatus.CAPTURE_STOPPED


def test_decline_transcribe() -> None:
    assert (
        apply_transition(SessionStatus.RECORDED, "decline_transcribe")
        == SessionStatus.PENDING_AUDIO_DISPOSAL
    )


def test_invalid_transition() -> None:
    with pytest.raises(InvalidTransitionError):
        apply_transition(SessionStatus.COMPLETED, "stop_recording")
