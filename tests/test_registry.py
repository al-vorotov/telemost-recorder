from providers.registry import detect_provider


def test_detect_telemost_url() -> None:
    assert detect_provider("https://telemost.yandex.ru/j/12345678901234") == "telemost"


def test_detect_unknown_url() -> None:
    assert detect_provider("https://zoom.us/j/123") is None
