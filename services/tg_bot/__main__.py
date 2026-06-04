import asyncio
import logging

from services.tg_bot.bot import run_bot

logging.basicConfig(level=logging.INFO)


def main() -> None:
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
