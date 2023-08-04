import os
import json
import shutil
from typing import Optional, Dict, Any
import discord
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

    @dc.command()
    async def download_data(self, ctx: dc.Context[Bot]) -> None:
        """Download a copy of your data for backup purpose.
        It is recommended to run this command on my DM channel to avoid other users from seeing your data.
        """
        user = await self.get_user_data(ctx)
        utc_offset_hour = user.utc_offset_hour.value
        uid = str(ctx.author.id)
        data: Dict[str, Any] = {}

        user_data = await self.db.get_user_data(uid)

        data["user"] = user_data.as_json() if user_data else None
        data["tasks"] = [
            t.as_json()
            for t in await self.db.get_user_tasks(uid, utc_offset_hour=utc_offset_hour)
        ]
        data["shortcuts"] = await self.db.get_all_command_shortcuts(uid)

        folder = f"__TEMP__.{uid}"
        filename = "watdo.data.json"
        filepath = os.path.join(folder, filename)

        os.makedirs(folder, exist_ok=True)

        with open(filepath, "w") as file:
            json.dump(data, file, indent=4)

        with open(filepath) as file:
            await ctx.send(file=discord.File(file, filename=filename, spoiler=True))

        shutil.rmtree(folder, ignore_errors=True)


async def setup(bot: Bot) -> None:
    await bot.add_cog(Miscellaneous(bot, bot.db))
