import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_transcriber() -> None:
    logger.info("transcriber stub — waiting for transcription.jobs")
    # TODO: Redis consumer + FasterWhisperBackend
    while True:
        await asyncio.sleep(60)


def main() -> None:
    asyncio.run(run_transcriber())


if __name__ == "__main__":
    main()
