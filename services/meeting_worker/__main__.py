import argparse
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_worker(session_id: str) -> None:
    logger.info("meeting-worker stub for session %s", session_id)
    # TODO: consume session.commands from Redis, drive MeetingProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Meeting worker for one session")
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()
    asyncio.run(run_worker(args.session_id))


if __name__ == "__main__":
    main()
