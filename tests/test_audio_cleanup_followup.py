from services.gateway.services.audio_cleanup_followup import _classify_followup_action


def test_followup_classify_none_before_reminder() -> None:
    assert (
        _classify_followup_action(
            age_min=29,
            reminder_after=30,
            auto_after=180,
            interval=10,
        )
        is None
    )


def test_followup_classify_reminder_window() -> None:
    assert _classify_followup_action(
        age_min=35,
        reminder_after=30,
        auto_after=180,
        interval=10,
    ) == "remind"


def test_followup_classify_auto_after_timeout() -> None:
    assert _classify_followup_action(
        age_min=181,
        reminder_after=30,
        auto_after=180,
        interval=10,
    ) == "auto"
