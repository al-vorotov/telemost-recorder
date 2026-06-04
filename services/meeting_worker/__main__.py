import argparse
import asyncio
import logging
from uuid import UUID

from services.meeting_worker.runner import MeetingWorkerRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run_worker(session_id: str) -> None:
    runner = MeetingWorkerRunner(UUID(session_id))
    await runner.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="Meeting worker for one session")
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()
    logger.info("Starting meeting worker for %s", args.session_id)
    asyncio.run(run_worker(args.session_id))


if __name__ == "__main__":
    main()
