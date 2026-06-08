import re
from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from providers.registry import detect_provider

_TELEMOST_URL_RE = re.compile(r"https?://telemost\.yandex\.\w+/j/\S+", re.IGNORECASE)
_DATETIME_RE = re.compile(
    r"^(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})$"
)


def extract_meeting_url(text: str) -> str | None:
    match = _TELEMOST_URL_RE.search(text.strip())
    return match.group(0) if match else None


def parse_session_id(data: str) -> tuple[str, UUID] | None:
    if ":" not in data:
        return None
    action, sid = data.split(":", 1)
    try:
        return action, UUID(sid)
    except ValueError:
        return None


def validate_link(text: str) -> str | None:
    url = extract_meeting_url(text)
    if url and detect_provider(url):
        return url
    return None


def parse_schedule_datetime(text: str, tz_name: str = "Europe/Moscow") -> datetime | None:
    """Парсит «ДД.ММ.ГГГГ ЧЧ:ММ» в aware datetime."""
    m = _DATETIME_RE.match(text.strip())
    if not m:
        return None
    day, month, year, hour, minute = map(int, m.groups())
    try:
        return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz_name))
    except ValueError:
        return None
