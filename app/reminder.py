import asyncio
import datetime as dt
from app.discord import Bot
from app.database import Database


class Reminder:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        database: Database,
        bot: Bot,
    ) -> None:
        self.loop = loop
        self.db = database
        self.bot = bot

    async def _run(self) -> None:
        pass
        # while True:
        #     async for key in self.db.iter_keys("tasks*"):
        #         uid = key.split(".")[1]

        #         for task in await self.db.get_user_tasks(uid):
        #             date = task.due_date

        #             if date is None:
        #                 continue

        #             if date <= dt.datetime.now():
        #                 print(f"REMIND!!! {task.title.value}")

        #     await asyncio.sleep(1)

    def start(self) -> None:
        self.loop.create_task(self._run())
