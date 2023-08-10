import asyncio
from typing import TYPE_CHECKING
import discord
from watdo import dt
from watdo.models import Task, User
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

    async def remind(self, user: discord.User, task: Task) -> None:
        if not task.is_done and task.has_reminder.value:
            if task.channel_id is None:
                channel = user
            else:
                channel = self.bot.get_channel(task.channel_id.value)

                if channel is None:
                    channel = user

            content = f"⏰ **Reminder** for {user.mention}"
            embed = TaskEmbed(self.bot, task)

            try:
                await channel.send(content, embed=embed)
            except discord.HTTPException:
                try:
                    await user.send(content, embed=embed)
                except discord.HTTPException:
                    pass

    async def _update_task(
        self,
        user: discord.User,
        user_data: User,
        task: Task,
    ) -> None:
        old_task_str = task.as_json_str()
        utc_offset_hour = task.utc_offset_hour.value

        if task.is_recurring:
            ts = task.rrule.after(dt.date_now(utc_offset_hour)).timestamp()
            task.next_reminder = Timestamp(ts)
        else:
            task.next_reminder = None

        await self.db.set_user_task(user_data, old_task_str=old_task_str, new_task=task)
        await self.remind(user, task)

        if task.is_auto_done.value:
            await self.db.done_user_task(user_data, task)

    async def _run(self) -> None:
        while True:
            async for key in self.db.iter_keys("tasks*"):
                uid = key.split(".")[1]
                user_data = await self.db.get_user_data(uid)

                if user_data is None:
                    continue

                utc_offset_hour = user_data.utc_offset_hour.value

                for task_index, task in enumerate(
                    await self.db.get_user_tasks(user_data)
                ):
                    if task.next_reminder is None:
                        continue

                    if (
                        task.next_reminder.value
                        <= dt.date_now(utc_offset_hour).timestamp()
                    ):
                        user = self.bot.get_user(int(uid))

                        if user is None:
                            continue

                        self.bot.loop.create_task(
                            self._update_task(user, user_data, task)
                        )

            await asyncio.sleep(1)

    def start(self) -> None:
        self.loop.create_task(self._run())
