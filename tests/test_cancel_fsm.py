from services.gateway.services.session_fsm import apply_transition
from shared.contracts.session import SessionStatus


def test_cancel_scheduled() -> None:
    assert apply_transition(SessionStatus.SCHEDULED, "cancel") == SessionStatus.COMPLETED
