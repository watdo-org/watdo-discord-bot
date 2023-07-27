import asyncio
import datetime as dt
from app.discord import Bot
from app.database import Database
from app.safe_data import Timestamp
from app.discord.embeds import TaskEmbed


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
        while True:
            async for key in self.db.iter_keys("tasks*"):
                uid = key.split(".")[1]

                for task_index, task in enumerate(await self.db.get_user_tasks(uid)):
                    if task.next_reminder is None:
                        continue

                    if task.next_reminder.value <= dt.datetime.now().timestamp():
                        user = self.bot.get_user(int(uid))
                        self.bot.loop.create_task(
                            user.send(
                                "Please do this task!!",
                                embed=TaskEmbed(self.bot, task),
                            )
                        )

                        if task.is_recurring:
                            ts = task.rrule.after(dt.datetime.now()).timestamp()
                            task.next_reminder = Timestamp(ts)
                        else:
                            task.next_reminder = None

                        self.bot.loop.create_task(
                            self.db.set_user_task(uid, task_index, task)
                        )

            await asyncio.sleep(1)

    def start(self) -> None:
        self.loop.create_task(self._run())
