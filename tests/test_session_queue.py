import pytest

pytest.importorskip("redis")

from shared.queues.session_queue import SessionCommand, SessionEvent, SessionQueue


@pytest.mark.asyncio
async def test_publish_command_and_event() -> None:
    import redis.asyncio as redis

    queue = SessionQueue("redis://localhost:6379/15")
    try:
        await queue._redis.ping()
    except (redis.ConnectionError, OSError):
        pytest.skip("Redis not running on localhost:6379")
    try:
        cmd_id = await queue.publish_command(
            SessionCommand(session_id="test-session", action="STOP_CAPTURE")
        )
        assert cmd_id
        ev_id = await queue.publish_event(
            SessionEvent(session_id="test-session", event="recording")
        )
        assert ev_id
    finally:
        await queue.close()
