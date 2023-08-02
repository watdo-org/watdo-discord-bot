import math
import time
import datetime as dt
from typing import Optional, Tuple
import recurrent
import dateparser
import discord
from discord.ext import commands as dc
from watdo.models import Task, User
from watdo.discord import Bot
from watdo.safe_data import Timestamp, UTCOffsetHour
from watdo.discord.cogs import BaseCog
from watdo.discord.embeds import Embed, TaskEmbed, PagedEmbed


class Tasks(BaseCog):
    @dc.command()
    async def summary(self, ctx: dc.Context[Bot]) -> None:
        """Show the summary of all your tasks."""
        tasks = await self.db.get_user_tasks(str(ctx.author.id))
        embed = Embed(self.bot, "TASKS SUMMARY")
        embed.add_field(name="Total", value=len(tasks))
        embed.add_field(
            name="Important",
            value=sum(1 for t in tasks if t.is_important.value),
        )
        await ctx.send(embed=embed)

    def _parse_due(self, due: str, utc_offset_hour: float) -> Optional[float | str]:
        date = dateparser.parse(due)

        if date is not None:
            return date.timestamp()

        rr: Optional[str | dt.datetime] = recurrent.parse(due)

        if isinstance(rr, str):
            if "DTSTART:" not in rr:
                date_now = dt.datetime.now()
                d = date_now.strftime("%Y%m%dT%H%M%S")
                rr = f"DTSTART:{d}\n{rr}"

            return rr

        if isinstance(rr, dt.datetime):
            return rr.timestamp()

        return None

    async def _validate_utc_offset(self, message: discord.Message) -> Optional[float]:
        try:
            return UTCOffsetHour(float(message.content)).value
        except Exception:
            await message.reply(
                "Please only send a number between -24 and 24.\n"
                "Example: `8` for UTC+8."
            )
            return None

    @dc.command()
    async def todo(
        self,
        ctx: dc.Context[Bot],
        title: str,
        category: str,
        is_important: bool,
        due: Optional[str] = None,
    ) -> None:
        """Add a task to do."""
        uid = str(ctx.author.id)
        user = await self.db.get_user_data(uid)

        if user is None:
            utc_offset = (
                await self.interview(
                    ctx,
                    questions={
                        "What is your UTC offset?": self._validate_utc_offset,
                    },
                )
            )[0]
            user = User(utc_offset_hour=utc_offset, created_at=time.time())
            await self.db.set_user_data(uid, user)

        task = Task(
            title=title,
            category=category,
            is_important=is_important,
            due=self._parse_due(due, user.utc_offset_hour.value) if due else None,
            created_at=time.time(),
        )

        if task.due_date:
            task.next_reminder = Timestamp(task.due_date.timestamp())

        await self.db.add_user_task(uid, task)
        await ctx.send(embed=TaskEmbed(self.bot, task))

    @dc.command(aliases=["do"])
    async def do_priority(
        self,
        ctx: dc.Context[Bot],
        category: Optional[str] = None,
    ) -> None:
        """Show priority tasks."""
        tasks = await self.db.get_user_tasks(
            str(ctx.author.id),
            category=category,
            ignore_done=True,
        )
        tasks.sort(key=lambda t: t.is_important.value, reverse=True)
        tasks.sort(key=lambda t: t.due_date.timestamp() if t.due_date else math.inf)

        if not tasks:
            await ctx.send("No tasks.")
            return

        paged_embed = PagedEmbed(self.bot)
        paged_embed.add_pages(*(TaskEmbed(self.bot, t) for t in tasks))
        paged_embed.send(ctx)

    async def _confirm_task_action(
        self, ctx: dc.Context[Bot], title: str
    ) -> Tuple[Optional[discord.Message], Optional[Task]]:
        task = await self.db.get_user_task(str(ctx.author.id), title)

        if task is None:
            await ctx.send(f'"{title}" not found ❌')
            return None, None

        message = await ctx.send("Are you sure?", embed=TaskEmbed(self.bot, task))
        is_confirm = await self.wait_for_confirmation(ctx, message)

        if is_confirm:
            return message, task

        return None, None

    @dc.command()
    async def done(self, ctx: dc.Context[Bot], title: str) -> None:
        """Remove a task."""
        uid = str(ctx.author.id)
        message, task = await self._confirm_task_action(ctx, title)

        if (message is not None) and (task is not None):
            old_task_str = task.as_json_str()
            task.last_done = Timestamp(time.time())
            await self.db.set_user_task(uid, old_task_str, task)

            if not task.is_recurring:
                await self.db.remove_user_task(uid, task)

            await message.edit(content="Done ✅")

    @dc.command()
    async def cancel(self, ctx: dc.Context[Bot], title: str) -> None:
        """Cancel a task."""
        message, task = await self._confirm_task_action(ctx, title)

        if (message is not None) and (task is not None):
            await self.db.remove_user_task(str(ctx.author.id), task)
            await message.edit(content="Cancelled ✅")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tasks(bot, bot.db))
