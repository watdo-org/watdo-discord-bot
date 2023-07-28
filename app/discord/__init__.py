import os
import glob
import asyncio
from typing import Any
import discord
from discord.ext import commands as dc
from app.database import Database
from app.environ import DISCORD_TOKEN
from app.logging import get_logger
from app.reminder import Reminder
from app.discord.cogs import BaseCog


class Bot(dc.Bot):
    def __init__(self, loop: asyncio.AbstractEventLoop, database: Database) -> None:
        super().__init__(
            loop=loop,
            command_prefix="watdo ",
            help_command=None,
            intents=discord.Intents.all(),
        )
        self.db = database
        self.color = discord.Colour.from_rgb(191, 155, 231)

        self.add_event("on_ready")
        self.add_event("on_command_error")

    def add_event(self, event_name: str) -> None:
        event = getattr(self, f"_{event_name}_event")

        async def event_wrapper(*args: Any, **kwargs: Any) -> None:
            try:
                await event(*args, **kwargs)
            except Exception as error:
                get_logger(f"Bot.{event_name}").exception(error)

        self.add_listener(event_wrapper, event_name)

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

    async def _on_ready_event(self) -> None:
        Reminder(self.loop, self.db, self).start()
        get_logger("Bot.on_ready").info("Bot is ready.")

    async def _on_command_error_event(
        self, ctx: dc.Context, error: dc.CommandError
    ) -> None:
        if isinstance(error, dc.MissingRequiredArgument):
            params = BaseCog.parse_params(ctx.command)
            await ctx.reply(f"{ctx.prefix}{ctx.invoked_with} {params}")
        else:
            await ctx.reply(error)
