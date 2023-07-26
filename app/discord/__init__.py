import os
import glob
import discord
from discord.ext import commands as dc
from app.database import Database
from app.environ import DISCORD_TOKEN


class Bot(dc.Bot):
    def __init__(self, database: Database) -> None:
        super().__init__(
            command_prefix="watdo ",
            help_command=None,
            intents=discord.Intents.all(),
        )
        self.db = database
        self.color = discord.Colour.from_rgb(191, 155, 231)

    async def start(self) -> None:
        # Load cogs
        for path in glob.iglob(
            os.path.join("app", "discord", "cogs", "**", "*"),
            recursive=True,
        ):
            if path.endswith("__init__.py"):
                continue

            if path.endswith(".py"):
                path = path.rstrip(".py").replace("/", ".")
                await self.load_extension(path)

        # Ensure docstring for all commands
        for cog in self.cogs.values():
            for command in cog.get_commands():
                if command.help is None:
                    raise Exception(
                        f"Please add docstring for {command.module}.{command.name}"
                    )

        await super().start(DISCORD_TOKEN)

    @staticmethod
    def parse_params(command: dc.Command) -> str:
        params = []

        for param in command.clean_params.values():
            t = param.annotation

            if t is bool:
                t = "yes/no"

            if t in (int, float):
                t = "number"

            t = f"*{t}*"
            p = param.name if param.annotation is str else f"{param.name}: {t}"
            p = p.replace("_", " ")

            if param.required:
                p = f"**[{p}]**"
            else:
                p = f"[{p}]"

            params.append(p)

        return " ".join(params)
