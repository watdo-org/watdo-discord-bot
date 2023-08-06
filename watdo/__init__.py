import asyncio
from watdo.discord import Bot
from watdo.environ import DISCORD_TOKEN
from watdo.database import Database
from watdo._main_runner import async_main_runner


class AppContext:
    def __init__(self) -> None:
        self.bot: Bot


app_context = AppContext()


async def async_main(loop: asyncio.AbstractEventLoop) -> int:
    db = Database()
    bot = Bot(loop, db)
    app_context.bot = bot

    await bot.start(DISCORD_TOKEN)

    return 0


def main() -> int:
    return async_main_runner(async_main)
