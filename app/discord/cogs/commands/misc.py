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

            cmds = []

            for c in commands:
                names = " or ".join(f"`{n}`" for n in [c.name] + c.aliases)
                params = self.parse_params(c)
                new_line = "\n" if params else ""
                cmds.append(f"{names}{new_line}{params}\n> {c.help}")

            embed.add_field(name=cog.qualified_name, value="\n\n".join(cmds))

        await ctx.send(embed=embed)

    @dc.command()
    async def ping(self, ctx: dc.Context) -> None:
        """Show the server latency."""
        await ctx.send(f"Pong! **{round(self.bot.latency * 1000)}ms**")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Miscellaneous(bot, bot.db))
