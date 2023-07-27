import math
import time
import datetime as dt
from typing import Optional
import humanize
import recurrent
import dateparser
from discord.ext import commands as dc
from app.models import Task
from app.discord import Bot
from app.discord.cogs import BaseCog
from app.discord.embeds import Embed, PagedEmbed


class Tasks(BaseCog):
    def create_task_embed(self, task: Task) -> Embed:
        embed = Embed(self.bot, task.title.value, timestamp=task.due_date)
        embed.add_field(name="Category", value=task.category.value)
        embed.add_field(
            name="Important", value="Yes" if task.is_important.value else "No"
        )
        embed.add_field(
            name="Created",
            value=f"{humanize.naturaldate(task.date_created).capitalize()} "
            f"({humanize.naturaltime(task.date_created)})",
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

    @dc.command()
    async def done(self, ctx: dc.Context, title: str) -> None:
        """Remove a task."""
        task = await self.db.get_user_task(ctx.author.id, title)

        if task is None:
            await ctx.send(f'"{title}" not found ❌')
            return

        message = await ctx.send("Are you sure?", embed=self.create_task_embed(task))
        confirm_remove = await self.wait_for_confirmation(ctx, message)

        if confirm_remove:
            await self.db.remove_user_task(ctx.author.id, task)
            await message.edit(content="Done ✅")

    @dc.command()
    async def cancel(self, ctx: dc.Context, title: str) -> None:
        """Cancel a task."""
        task = await self.db.get_user_task(ctx.author.id, title)

        if task is None:
            await ctx.send(f'"{title}" not found ❌')
            return

        message = await ctx.send("Are you sure?", embed=self.create_task_embed(task))
        confirm_remove = await self.wait_for_confirmation(ctx, message)

        if confirm_remove:
            await self.db.remove_user_task(ctx.author.id, task)
            await message.edit(content="Cancelled ✅")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tasks(bot, bot.db))
