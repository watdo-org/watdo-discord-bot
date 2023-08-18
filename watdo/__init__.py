import asyncio
from watdo.discord import Bot
from watdo.environ import DISCORD_TOKEN
from watdo._main_runner import async_main_runner


async def async_main(loop: asyncio.AbstractEventLoop) -> int:
    bot = Bot(loop=loop)

    await bot.start(DISCORD_TOKEN)

    return 0


def main() -> int:
    return async_main_runner(async_main)
