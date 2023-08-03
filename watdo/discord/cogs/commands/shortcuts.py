import discord
from discord.ext import commands as dc
from watdo.discord import Bot
from watdo.discord.cogs import BaseCog


class Shortcuts(BaseCog, description="Speed up your workflow with command shortcuts."):
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
            await ctx.send(f'"{message.content}" is not a command ❌')
            return

        await self.db.set_command_shortcut(str(ctx.author.id), name, message.content)
        await ctx.send(f"Command shortcut set ✅\n```\n{message.content}\n```{name}")

    @dc.command()
    async def shorts(self, ctx: dc.Context[Bot]) -> None:
        """Show all your command shortcuts."""
        data = await self.db.get_all_command_shortcuts(str(ctx.author.id))
        message = []

        for name, command in data.items():
            message.append(f"```\n{command}\n```{name}\n")

        await ctx.send("".join(message) or "No command shortcuts ❌")

    @dc.command()
    async def delete_short(self, ctx: dc.Context[Bot], name: str) -> None:
        """Delete a command shortcut."""
        deleted_count = await self.db.delete_command_shortcut(str(ctx.author.id), name)

        if deleted_count > 0:
            await ctx.send("Deleted ✅")
        else:
            await ctx.send(f'Command shortcut "{name}" not found ❌')


async def setup(bot: Bot) -> None:
    await bot.add_cog(Shortcuts(bot, bot.db))
