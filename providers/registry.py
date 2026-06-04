import re
from urllib.parse import urlparse

from providers.telemost.provider import TelemostProvider

_PROVIDERS = {
    "telemost": TelemostProvider(),
}

_TELEMOST_RE = re.compile(
    r"^https?://(telemost\.yandex\.(ru|com)|.*\.telemost\.yandex\.\w+)/j/",
    re.IGNORECASE,
)


def detect_provider(meeting_url: str) -> str | None:
    parsed = urlparse(meeting_url.strip())
    if not parsed.scheme or not parsed.netloc:
        return None
    if _TELEMOST_RE.match(meeting_url.strip()):
        return "telemost"
    return None


def get_provider(provider_id: str):
    return _PROVIDERS.get(provider_id)
