from typing import Optional
from discord.ext import commands as dc
from watdo.discord import Bot
from watdo.discord.cogs import BaseCog
from watdo.discord.embeds import Embed


class Miscellaneous(BaseCog):
    async def command_help(self, ctx: dc.Context[Bot], command_name: str) -> None:
        embed = Embed(self.bot, "Command Help")
        command = self.bot.get_command(command_name)

        if command is None:
            await ctx.send(f'Command "{command_name}" not found ❌')
            return

        embed.description = (
            " or ".join(f"`{n}`" for n in [command.name] + list(command.aliases))
            + f"\n{command.help}"
        )

        for param in self.parse_params_list(command):
            embed.add_field(
                name=f"{param.value}{' - optional' if not param.is_required else ''}",
                value=param.description or "No description.",
                inline=False,
            )

        await ctx.send(embed=embed)

    @dc.command()
    async def help(self, ctx: dc.Context[Bot], command: Optional[str] = None) -> None:
        """Show this help message."""
        if command is not None:
            await self.command_help(ctx, command)
            return

        embed = Embed(
            self.bot,
            "HELP",
            description="**Website:** https://nietsuu.github.io/watdo\n"
            "Type `watdo help [command]` for detailed command help.",
        )

        for cog in self.bot.cogs.values():
            commands = cog.get_commands()

            if not commands:
                continue

            cmds = []

            for c in commands:
                names = " or ".join(f"`{n}`" for n in [c.name] + list(c.aliases))
                params = self.parse_params(c)
                new_line = "\n" if params else ""
                cmds.append(f"{names}{new_line}{params}\n{c.help}")

            embed.add_field(
                name=cog.qualified_name,
                value=(f"{cog.description}\n" if cog.description else "")
                + "\n\n".join(cmds),
            )

        await ctx.send(embed=embed)

    @dc.command()
    async def ping(self, ctx: dc.Context[Bot]) -> None:
        """Show the server latency."""
        await ctx.send(f"Pong! **{round(self.bot.latency * 1000)}ms**")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Miscellaneous(bot, bot.db))
