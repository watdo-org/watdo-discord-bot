import asyncio
import datetime as dt
from typing import TYPE_CHECKING
from watdo.database import Database
from watdo.safe_data import Timestamp
from watdo.discord.embeds import TaskEmbed

if TYPE_CHECKING:
    from watdo.discord import Bot


class Reminder:
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        database: Database,
        bot: "Bot",
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

                        if user is None:
                            continue

                        if not task.is_done:
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
