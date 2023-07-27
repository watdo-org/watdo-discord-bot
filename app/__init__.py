import asyncio
from app.discord import Bot
from app.database import Database


async def main(loop: asyncio.AbstractEventLoop) -> None:
    db = Database()
    bot = Bot(loop, db)

    await bot.start()
