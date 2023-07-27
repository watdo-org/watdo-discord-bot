from discord.ext import commands as dc
from app.discord import Bot
from app.discord.cogs import BaseCog
from app.logging import get_logger
from app.reminder import Reminder


class Events(BaseCog):
    @dc.Cog.listener()
    async def on_ready(self) -> None:
        Reminder(self.bot.loop, self.db, self.bot).start()
        get_logger("Events.on_ready").info("Bot is ready.")

    @dc.Cog.listener()
    async def on_command_error(self, ctx: dc.Context, error: dc.CommandError) -> None:
        if isinstance(error, dc.MissingRequiredArgument):
            params = self.parse_params(ctx.command)
            await ctx.reply(f"{ctx.prefix}{ctx.invoked_with} {params}")
        else:
            await ctx.reply(error)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Events(bot, bot.db))
