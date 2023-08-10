from collections import defaultdict
from discord.ext import commands as dc
from watdo.models import Task
from watdo.discord import Bot
from watdo.discord.cogs import BaseCog
from watdo.discord.embeds import Embed


class Categories(BaseCog):
    """Manage your tasks categories."""

    @dc.command()
    async def clist(self, ctx: dc.Context[Bot]) -> None:
        """Show your tasks by category."""
        user = await self.get_user_data(ctx)
        tasks = await self.db.get_user_tasks(user)
        categories = defaultdict(list)

        for task in tasks:
            categories[task.category.value].append(task)

        embed = Embed(self.bot, "TASKS")

        for category, tasks in categories.items():
            embed.add_field(
                name=category,
                value=self.tasks_to_text(tasks, no_category=True)[:1024],
                inline=False,
            )

        await ctx.send(embed=embed)

    @dc.command(aliases=["rc"])
    async def rename_category(
        self, ctx: dc.Context[Bot], old_name: str, new_name: str
    ) -> None:
        """Rename a category."""
        new_name = new_name.strip()
        user = await self.get_user_data(ctx)
        tasks = await self.db.get_user_tasks(user, category=old_name)

        if len(tasks) == 0:
            await ctx.send(f'Category "{old_name}" not found ❌')
            return

        for task in tasks:
            old_task_str = task.as_json_str()
            task.category.set(new_name)
            self.bot.loop.create_task(
                self.db.set_user_task(user, old_task_str=old_task_str, new_task=task)
            )

        await ctx.send(f'Category "{old_name}" has been renamed to "{new_name}" ✅')

    async def _delete_category_task(
        self, ctx: dc.Context[Bot], uid: str, task: Task
    ) -> None:
        await self.db.remove_user_task(uid, task)
        await ctx.send(f'Task "{task.title.value}" has been removed ✅')

    @dc.command(aliases=["dc"])
    async def delete_category(self, ctx: dc.Context[Bot], name: str) -> None:
        """Delete a category."""
        uid = str(ctx.author.id)
        user = await self.get_user_data(ctx)
        tasks = await self.db.get_user_tasks(user, category=name)

        if len(tasks) == 0:
            await ctx.send(f'Category "{name}" not found ❌')
            return

        for task in tasks:
            self.bot.loop.create_task(self._delete_category_task(ctx, uid, task))


async def setup(bot: Bot) -> None:
    await bot.add_cog(Categories(bot, bot.db))
