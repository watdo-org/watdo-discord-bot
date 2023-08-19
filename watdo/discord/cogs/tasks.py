from discord.ext import commands as dc
from watdo.discord import Bot
from watdo.discord.cogs import BaseCog


class Tasks(BaseCog):
    @dc.hybrid_command()
    async def summary(self, ctx: dc.Context[Bot]) -> None:
        """Show the summary of all your tasks."""
        profile = await self.get_profile(ctx)
        await ctx.send(profile.uuid.value)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tasks(bot, bot.db))
