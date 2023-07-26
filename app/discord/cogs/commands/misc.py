from discord.ext import commands as dc
from app.discord import Bot
from app.discord.cogs import BaseCog
from app.discord.embeds import Embed


class Miscellaneous(BaseCog):
    @dc.command()
    async def help(self, ctx: dc.Context) -> None:
        """Show this help message."""
        embed = Embed(self.bot, "HELP")

        for cog in self.bot.cogs.values():
            commands = cog.get_commands()

            if not commands:
                continue

            cmds = "\n".join(
                f"{c.name} {self.parse_params(c)}\n> {c.help}" for c in commands
            )
            embed.add_field(name=cog.qualified_name, value=cmds)

        await ctx.send(embed=embed)

    @dc.command()
    async def ping(self, ctx: dc.Context) -> None:
        """Show the server latency."""
        await ctx.send(f"Pong! **{round(self.bot.latency * 1000)}ms**")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Miscellaneous(bot, bot.db))
