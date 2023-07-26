import math
from typing import Optional
import dateparser
from discord.ext import commands as dc
from app.models import Task
from app.discord import Bot
from app.discord.cogs import BaseCog
from app.discord.embeds import Embed


class Tasks(BaseCog):
    def create_task_embed(self, task: Task) -> Embed:
        embed = Embed(self.bot, task.title.value, timestamp=task.due_date)
        embed.add_field(name="Category", value=task.category.value)
        embed.add_field(
            name="Important", value="Yes" if task.is_important.value else "No"
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
        due_seconds = None

        if due is not None:
            date = dateparser.parse(due)
            due_seconds = date.timestamp() if date else None

        task = Task(
            title=title,
            category=category,
            is_important=is_important,
            due_seconds=due_seconds,
        )
        await self.db.add_user_task(ctx.author.id, task)
        await ctx.send(embed=self.create_task_embed(task))

    @dc.command()
    async def do_priority(
        self,
        ctx: dc.Context,
        limit: int = 5,
        category: Optional[str] = None,
    ) -> None:
        """Show priority tasks."""
        tasks = await self.db.get_user_tasks(ctx.author.id, category=category)
        tasks.sort(key=lambda t: t.is_important.value, reverse=True)
        tasks.sort(key=lambda t: t.due_seconds.value if t.due_seconds else math.inf)

        embeds = []
        for index, task in enumerate(tasks):
            if index == limit:
                break
            embeds.append(self.create_task_embed(task))

        if embeds:
            await ctx.send(embeds=embeds)
        else:
            await ctx.send("No tasks.")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tasks(bot, bot.db))
