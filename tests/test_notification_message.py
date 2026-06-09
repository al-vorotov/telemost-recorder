from shared.queues.session_queue import NotificationMessage


def test_notification_roundtrip() -> None:
    msg = NotificationMessage(
        telegram_id=42,
        text="test",
        session_id="abc",
        show_recording_controls=True,
        attach_transcript=True,
    )
    restored = NotificationMessage.from_payload(__import__("json").loads(msg.to_json()))
    assert restored.telegram_id == 42
    assert restored.show_recording_controls is True
    assert restored.attach_transcript is True
