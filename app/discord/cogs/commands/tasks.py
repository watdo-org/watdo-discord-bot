from discord.ext import commands as dc
from app.discord import Bot
from app.discord.cogs import BaseCog
from app.discord.embeds import Embed


class Tasks(BaseCog):
    @dc.command()
    async def summary(self, ctx: dc.Context) -> None:
        tasks = await self.db.get_user_tasks(ctx.author.id)
        embed = Embed(self.bot, "TASKS SUMMARY")
        embed.add_field(name="Total Tasks", value=len(tasks))
        await ctx.send(embed=embed)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tasks(bot, bot.db))
