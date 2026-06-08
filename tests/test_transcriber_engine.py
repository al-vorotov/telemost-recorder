from services.transcriber.engine import _format_timestamp


def test_format_timestamp() -> None:
    assert _format_timestamp(0) == "00:00"
    assert _format_timestamp(65.4) == "01:05"
    assert _format_timestamp(3661) == "61:01"
