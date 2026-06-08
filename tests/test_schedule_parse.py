from datetime import datetime
from zoneinfo import ZoneInfo

from services.tg_bot.handlers.common import parse_schedule_datetime


def test_parse_schedule_datetime() -> None:
    dt = parse_schedule_datetime("08.06.2026 14:30")
    assert dt is not None
    assert dt == datetime(2026, 6, 8, 14, 30, tzinfo=ZoneInfo("Europe/Moscow"))


def test_parse_invalid() -> None:
    assert parse_schedule_datetime("2026-06-08") is None
    assert parse_schedule_datetime("32.13.2026 25:99") is None
