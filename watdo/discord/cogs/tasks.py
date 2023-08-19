from typing import Dict
from discord.ext import commands as dc
from watdo.models import Task, ScheduledTask
from watdo.discord import Bot
from watdo.discord.cogs import BaseCog
from watdo.discord.embeds import Embed


class Tasks(BaseCog):
    @dc.hybrid_command()  # type: ignore[arg-type]
    async def summary(self, ctx: dc.Context[Bot]) -> None:
        """Show the summary of all your tasks."""
        profile = await self.get_profile(ctx)
        tasks = await Task.get_tasks_of_profile(self.db, profile)

        embed = Embed(self.bot, "TASKS SUMMARY")

        total = 0
        is_important = 0
        overdue = 0
        recurring = 0
        one_time = 0
        done = 0
        max_categ_len = 0
        categories: Dict[str, int] = {}

        for task in tasks:
            total += 1

            if task.is_important.value:
                is_important += 1

            if isinstance(task, ScheduledTask):
                if task.is_overdue:
                    overdue += 1

            if isinstance(task, ScheduledTask) and task.is_recurring:
                recurring += 1
            else:
                one_time += 1

            if task.is_done:
                done += 1

            if len(task.category.value) > max_categ_len:
                max_categ_len = len(task.category.value)

            try:
                categories[task.category.value] += 1
            except KeyError:
                categories[task.category.value] = 1

        embed.add_field(name="Total", value=total)
        embed.add_field(name="Important", value=is_important)
        embed.add_field(name="Overdue", value=overdue)
        embed.add_field(name="Recurring", value=recurring)
        embed.add_field(name="One-Time", value=one_time)
        embed.add_field(name="Done", value=done)

        if categories:
            c = "\n".join(
                f"{k.ljust(max_categ_len)}  {v}" for k, v in categories.items()
            )
            embed.add_field(
                name="Categories", value=f"```\n{c[:1000]}\n```", inline=False
            )

        await ctx.send(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tasks(bot, bot.db))
