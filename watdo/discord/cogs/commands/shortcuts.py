import discord
from discord.ext import commands as dc
from watdo.discord import Bot
from watdo.discord.cogs import BaseCog


class Shortcuts(BaseCog):
    """Speed up your workflow with command shortcuts."""

    @dc.command()
    async def set_short(
        self,
        ctx: dc.Context[Bot],
        name: str,
        message: discord.Message,
    ) -> None:
        """Set a command shortcut.
        When you type in the **name**, **message** will execute."""
        if not message.content.startswith(str(self.bot.command_prefix)):
            await ctx.send(f"'{message.content}' is not a command ❌")
            return

        await self.db.set_command_shortcut(str(ctx.author.id), name, message.content)
        await ctx.send(f"Command shortcut set ✅\n```\n{name} = {message.content}\n```")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Shortcuts(bot, bot.db))
