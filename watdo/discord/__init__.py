import os
import glob
import logging
import asyncio
from typing import cast, Any
import discord
from discord.ext import commands as dc
from watdo.environ import IS_DEV
from watdo.database import Database
from watdo.logging import get_logger
from watdo.reminder import Reminder
from watdo.discord.cogs import BaseCog
from watdo.discord.embeds import ErrorEmbed


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
                raise error

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
                path = path.rstrip(".py").replace("/", ".").replace("\\", ".")
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
        try:
            bot_user = cast(discord.User, self.user)

            if message.channel.id == 1028932255256682536:
                if not IS_DEV:
                    return
            else:
                if IS_DEV:
                    return

            if message.author.id == bot_user.id:
                return

            if not message.content.startswith(str(self.command_prefix)):
                self.loop.create_task(self.process_shortcut_commands(message))

                if bot_user.mention in message.content.replace("<@!", "<@"):
                    await message.reply(f"Type `{self.command_prefix}help` for help.")

            else:
                await self.process_commands(message)
        except Exception as error:
            get_logger("Bot.on_message").exception(error)
            raise error

    async def process_shortcut_commands(self, message: discord.Message) -> None:
        command = await self.db.get_command_shortcut(
            str(message.author.id),
            message.content,
        )

        if command is not None:
            message.content = command
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
        elif isinstance(error, dc.CommandNotFound):
            await ctx.send(f'No command "{ctx.invoked_with}" ❌')
        else:
            await ctx.send(f"**{type(error).__name__}:** {error}")

    def log(self, record: logging.LogRecord) -> None:
        channel = self.get_channel(1086519345972260894)
        self.loop.create_task(channel.send(embed=ErrorEmbed(record)))
