import math
import time
import datetime as dt
from typing import Optional, Tuple
import humanize
import recurrent
import dateparser
import discord
from discord.ext import commands as dc
from app.models import Task
from app.discord import Bot
from app.safe_data import Number
from app.discord.cogs import BaseCog
from app.discord.embeds import Embed, PagedEmbed


class Tasks(BaseCog):
    def create_task_embed(self, task: Task) -> Embed:
        embed = Embed(self.bot, task.title.value, timestamp=task.due_date)
        author = "📝"

        if task.is_recurring:
            author = "🔁"
        elif task.due_date:
            author = "🔔"

        embed.set_author(
            name=f"{'📌 ' if task.is_important.value else ''}"
            f"{author} {task.category.value}"
        )
        embed.add_field(
            name="Created",
            value=f"{humanize.naturaldate(task.date_created).capitalize()} "
            f"({humanize.naturaltime(task.date_created)})",
        )

        if task.last_done is not None:
            embed.add_field(
                name="Last Done",
                value=f"{humanize.naturaldate(task.last_done_date).capitalize()} "
                f"({humanize.naturaltime(task.last_done_date)})",
            )

        return embed

    @dc.command()
    async def summary(self, ctx: dc.Context) -> None:
        """Show the summary of all your tasks."""
        tasks = await self.db.get_user_tasks(ctx.author.id)
        embed = Embed(self.bot, "TASKS SUMMARY")
        embed.add_field(name="Total", value=len(tasks))
        embed.add_field(
            name="Important",
            value=sum(1 for t in tasks if t.is_important.value),
        )
        await ctx.send(embed=embed)

    def _parse_due(self, due: str) -> Optional[float | str]:
        date = dateparser.parse(due)

        if date is not None:
            return date.timestamp()

        rr: Optional[str | dt.datetime] = recurrent.parse(due)

        if isinstance(rr, str):
            return rr

        if isinstance(rr, dt.datetime):
            return rr.timestamp()

        return None

    @dc.command()
    async def todo(
        self,
        ctx: dc.Context,
        title: str,
        category: str,
        is_important: bool,
        due: Optional[str] = None,
    ) -> None:
        """Add a task to do."""
        task = Task(
            title=title,
            category=category,
            is_important=is_important,
            due=self._parse_due(due) if due else None,
            last_done=None,
            created_at=time.time(),
        )
        await self.db.add_user_task(ctx.author.id, task)
        await ctx.send(embed=self.create_task_embed(task))

    @dc.command()
    async def do_priority(
        self,
        ctx: dc.Context,
        category: Optional[str] = None,
    ) -> None:
        """Show priority tasks."""
        tasks = await self.db.get_user_tasks(ctx.author.id, category=category)
        tasks.sort(key=lambda t: t.is_important.value, reverse=True)
        tasks.sort(key=lambda t: t.due_date.timestamp() if t.due_date else math.inf)

        if not tasks:
            await ctx.send("No tasks.")
            return

        paged_embed = PagedEmbed(self.bot)
        paged_embed.add_pages(*(self.create_task_embed(t) for t in tasks))
        paged_embed.send(ctx)

    async def _confirm_task_action(
        self, ctx: dc.Context, title: str
    ) -> Tuple[Optional[discord.Message], Optional[int], Optional[Task]]:
        index, task = await self.db.get_user_task(ctx.author.id, title)

        if task is None:
            await ctx.send(f'"{title}" not found ❌')
            return None, None, None

        message = await ctx.send("Are you sure?", embed=self.create_task_embed(task))
        is_confirm = await self.wait_for_confirmation(ctx, message)

        if is_confirm:
            return message, index, task

        return None, None, None

    @dc.command()
    async def done(self, ctx: dc.Context, title: str) -> None:
        """Remove a task."""
        message, task_index, task = await self._confirm_task_action(ctx, title)

        if (message is not None) and (task_index is not None) and (task is not None):
            if task.is_recurring:
                task.last_done = Number(time.time(), min_val=0, max_val=math.inf)
                await self.db.set_user_task(ctx.author.id, task_index, task)
            else:
                await self.db.remove_user_task(ctx.author.id, task)

            await message.edit(content="Done ✅")

    @dc.command()
    async def cancel(self, ctx: dc.Context, title: str) -> None:
        """Cancel a task."""
        message, task_index, task = await self._confirm_task_action(ctx, title)

        if message is not None and task is not None:
            await self.db.remove_user_task(ctx.author.id, task)
            await message.edit(content="Cancelled ✅")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tasks(bot, bot.db))
