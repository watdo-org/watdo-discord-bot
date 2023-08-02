import os
import glob
import asyncio
from typing import cast, Any
import discord
from discord.ext import commands as dc
from watdo.environ import IS_DEV
from watdo.database import Database
from watdo.logging import get_logger
from watdo.reminder import Reminder
from watdo.discord.cogs import BaseCog


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

    async def start(self, token: str, *, reconnect: bool = True) -> None:
        # Load cogs
        for path in glob.iglob(
            os.path.join("watdo", "discord", "cogs", "**", "*"),
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

        await super().start(token, reconnect=reconnect)

    async def on_message(self, message: discord.Message) -> None:
        bot_user = cast(discord.User, self.user)

        if message.author.id == bot_user.id:
            return

        if bot_user.mention in message.content.replace("<@!", "<@"):
            await message.reply(f"Type `{self.command_prefix}help` for help.")

        if message.channel.id == 1028932255256682536:
            if IS_DEV:
                await self.process_commands(message)
        else:
            if not IS_DEV:
                await self.process_commands(message)

    async def _on_ready_event(self) -> None:
        Reminder(self.loop, self.db, self).start()
        get_logger("Bot.on_ready").info("Bot is ready.")

    async def _on_command_error_event(
        self, ctx: dc.Context["Bot"], error: dc.CommandError
    ) -> None:
        if isinstance(error, dc.MissingRequiredArgument) and ctx.command is not None:
            params = BaseCog.parse_params(ctx.command)
            await ctx.send(f"{ctx.prefix}{ctx.invoked_with} {params}")
        else:
            await ctx.send(f"**{type(error).__name__}:** {error}")
