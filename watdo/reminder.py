import asyncio
from typing import TYPE_CHECKING, Any
import discord
from watdo import dt
from watdo.models import Profile, Task, ScheduledTask
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

    async def remind(self, task: ScheduledTask[str] | ScheduledTask[float]) -> None:
        if not task.is_done and task.has_reminder.value:
            channel_id = task.channel_id.value
            user = self.bot.get_user(task.created_by.value)
            channel: Any = (
                self.bot.get_channel(channel_id)
                or self.bot.get_user(channel_id)
                or user
            )

            if channel is None:
                return

            content = f"⏰ **Reminder** {'@here' if user is None else user.mention}"
            embed = TaskEmbed(self.bot, task)

            try:
                await channel.send(content, embed=embed)
            except discord.HTTPException:
                pass

    async def _update_task(
        self,
        profile: Profile,
        task: ScheduledTask[str] | ScheduledTask[float],
    ) -> None:
        utc_offset = profile.utc_offset.value

        if task.is_recurring:
            ts = task.rrule.after(dt.date_now(utc_offset)).timestamp()
            task.next_reminder = Timestamp(ts)
        else:
            task.next_reminder = None

        await task.save()
        await self.remind(task)

        if task.is_auto_done.value:
            await task.done()

    async def _run(self) -> None:
        while True:
            async for key in self.db.iter_keys("tasks:profile.*"):
                profile_id = key.split(".")[1]
                profile = await Profile.from_id(self.db, profile_id)

                if profile is None:
                    continue

                utc_offset = profile.utc_offset.value

                for task_index, task in enumerate(
                    await Task.get_tasks_of_profile(self.db, profile)
                ):
                    if not isinstance(task, ScheduledTask):
                        continue

                    if task.next_reminder is None:
                        continue

                    if task.next_reminder.value <= dt.date_now(utc_offset).timestamp():
                        self.bot.loop.create_task(self._update_task(profile, task))

            await asyncio.sleep(1)

    def start(self) -> None:
        self.loop.create_task(self._run())
