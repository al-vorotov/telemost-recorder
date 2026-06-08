import asyncio
import logging

from services.transcriber.runner import TranscriberRunner

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def run_transcriber() -> None:
    runner = TranscriberRunner()
    await runner.run()


def main() -> None:
    logger.info("Starting transcriber service")
    asyncio.run(run_transcriber())


if __name__ == "__main__":
    main()
