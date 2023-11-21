import os
import glob
import asyncio
import logging
from typing import cast, Any, List
import discord
from discord.ext import commands as dc
from watdo import dt
from watdo.errors import CancelCommand
from watdo.environ import IS_DEV, SYNC_SLASH_COMMANDS
from watdo.logging import get_logger
from watdo.reminder import Reminder
from watdo.database import Database
from watdo.discord.cogs import BaseCog
from watdo.discord.embeds import ErrorEmbed


class Bot(dc.Bot):
    def __init__(self, *, loop: asyncio.AbstractEventLoop, database: Database) -> None:
        super().__init__(
            loop=loop,
            command_prefix="$" if IS_DEV else "watdo ",
            help_command=None,
            intents=discord.Intents.all(),
        )
        self.db = database
        self.color = discord.Colour.from_rgb(191, 155, 231)

        for name in dir(self):
            if name.startswith("_on_") and name.endswith("_event"):
                self._add_event(name.lstrip("_").rstrip("_event"))

    def _add_event(self, event_name: str) -> None:
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

    async def _process_commands(
        self, command: List[str], message: discord.Message
    ) -> None:
        try:
            # Remove command the same as the trigger message to avoid infinite loop
            command.remove(message.content)
        except ValueError:
            pass

        for c in command:
            message.content = c
            await self.on_message(message)

    async def process_command_shortcuts(self, message: discord.Message) -> bool:
        command = await self.db.get_command_shortcut(
            str(message.author.id),
            message.content,
        )

        if command is None:
            return False

        self.loop.create_task(self._process_commands(command, message))
        return True

    async def on_message(self, message: discord.Message) -> None:
        try:
            await self.process_command_shortcuts(message)

            bot_user = cast(discord.User, self.user)

            if message.author.id == bot_user.id:
                return

            if not message.content.startswith(str(self.command_prefix)):
                if bot_user.mention in message.content.replace("<@!", "<@"):
                    await BaseCog.send(
                        message.channel, f"Type `{self.command_prefix}help` for help."
                    )

            else:
                await self.process_commands(message)
        except Exception as error:
            get_logger("Bot.on_message").exception(error)
            raise error

    async def _on_ready_event(self) -> None:
        logger = get_logger("Bot.on_ready")
        logger.info("watdo is ready!!")

        Reminder(self.loop, self.db, self).start()

        logger.debug(f"Timezone: {dt.local_tz()}")

        if SYNC_SLASH_COMMANDS:
            logger.debug("Syncing slash commands...")

            if IS_DEV:
                dev_server = cast(discord.Guild, self.get_guild(975234089353351178))
                self.tree.copy_global_to(guild=dev_server)
                synced_commands = await self.tree.sync(guild=dev_server)
            else:
                synced_commands = await self.tree.sync()

            logger.debug(f"Synced {len(synced_commands)} slash command(s)")

    async def _on_command_error_event(
        self, ctx: dc.Context["Bot"], error: dc.CommandError
    ) -> None:
        if isinstance(error, dc.MissingRequiredArgument) and ctx.command is not None:
            params = BaseCog.parse_params(ctx.command)
            await BaseCog.send(ctx, f"{ctx.prefix}{ctx.invoked_with} {params}")
        elif isinstance(error, dc.CommandNotFound):
            await BaseCog.send(ctx, f'No command "{ctx.invoked_with}" ❌')
        elif isinstance(error, CancelCommand):
            pass
        else:
            await BaseCog.send(ctx, f"**{type(error).__name__}:** {error}")

    def log(self, record: logging.LogRecord) -> None:
        channel = cast(discord.TextChannel, self.get_channel(1086519345972260894))
        self.loop.create_task(BaseCog.send(channel, embed=ErrorEmbed(record)))

    async def remove_reaction(
        self,
        message: discord.Message,
        *,
        reaction: str,
        user: discord.User,
    ) -> None:
        try:
            await message.remove_reaction(reaction, user)
        except discord.HTTPException:
            pass
