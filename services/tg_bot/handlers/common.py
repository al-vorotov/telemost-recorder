import re
from uuid import UUID

from providers.registry import detect_provider

_TELEMOST_URL_RE = re.compile(r"https?://telemost\.yandex\.\w+/j/\S+", re.IGNORECASE)


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
