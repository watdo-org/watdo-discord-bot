from collections import defaultdict
from discord.ext import commands as dc
from watdo.models import Task
from watdo.discord import Bot
from watdo.discord.cogs import BaseCog
from watdo.discord.embeds import Embed


class Categories(BaseCog):
    """Manage your tasks categories."""

    @dc.hybrid_command()  # type: ignore[arg-type]
    async def clist(self, ctx: dc.Context[Bot]) -> None:
        """Show your tasks by category."""
        profile = await self.get_profile(ctx)
        tasks_coll = await Task.get_tasks_of_profile(self.db, profile)
        categories = defaultdict(list)

        for task in tasks_coll:
            categories[task.category.value].append(task)

        embed = Embed(self.bot, "TASKS")

        for category, tasks in categories.items():
            embed.add_field(
                name=category,
                value=self.tasks_to_text(tasks, no_category=True)[:1024],
                inline=False,
            )

        await BaseCog.send(ctx, embed=embed)

    @dc.hybrid_command(aliases=["rc"])  # type: ignore[arg-type]
    async def rename_category(
        self, ctx: dc.Context[Bot], old_name: str, new_name: str
    ) -> None:
        """Rename a category."""
        new_name = new_name.strip()
        profile = await self.get_profile(ctx)
        tasks = await Task.get_tasks_of_profile(self.db, profile, category=old_name)

        if len(tasks) == 0:
            await BaseCog.send(ctx, f'Category "{old_name}" not found ❌')
            return

        for task in tasks:
            task.category.set(new_name)
            self.bot.loop.create_task(task.save())

        await BaseCog.send(
            ctx, f'Category "{old_name}" has been renamed to "{new_name}" ✅'
        )

    async def _delete_category_task(
        self, ctx: dc.Context[Bot], uid: str, task: Task
    ) -> None:
        await task.delete()
        await BaseCog.send(ctx, f'Task "{task.title.value}" has been removed ✅')

    @dc.hybrid_command(aliases=["dc"])  # type: ignore[arg-type]
    async def delete_category(self, ctx: dc.Context[Bot], name: str) -> None:
        """Delete a category."""
        uid = str(ctx.author.id)
        profile = await self.get_profile(ctx)
        tasks = await Task.get_tasks_of_profile(self.db, profile, category=name)

        if len(tasks) == 0:
            await BaseCog.send(ctx, f'Category "{name}" not found ❌')
            return

        for task in tasks:
            self.bot.loop.create_task(self._delete_category_task(ctx, uid, task))


async def setup(bot: Bot) -> None:
    await bot.add_cog(Categories(bot, bot.db))
