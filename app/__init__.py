import asyncio
from app.discord import Bot
from app.database import Database
from app.reminder import Reminder


async def main(loop: asyncio.AbstractEventLoop) -> None:
    db = Database()
    bot = Bot(loop, db)

    Reminder(loop, db, bot).start()
    await bot.start()
