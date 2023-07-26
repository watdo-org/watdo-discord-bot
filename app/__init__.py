import asyncio
from app.database import Database


async def main(loop: asyncio.AbstractEventLoop) -> None:
    db = Database()
