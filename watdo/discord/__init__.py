import os
import glob
import asyncio
from typing import cast, Any
import discord
from discord.ext import commands as dc
from watdo import dt
from watdo.errors import CancelCommand
from watdo.environ import IS_DEV, SYNC_SLASH_COMMANDS
from watdo.logging import get_logger
from watdo.database import Database
from watdo.discord.cogs import BaseCog


class Bot(dc.Bot):
    def __init__(self, *, loop: asyncio.AbstractEventLoop, database: Database) -> None:
        super().__init__(loop=loop, command_prefix="$", intents=discord.Intents.all())
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

    async def _on_ready_event(self) -> None:
        logger = get_logger("Bot.on_ready")
        logger.info("watdo is ready!!")
        logger.debug(f"Timezone: {dt.local_tz()}")
        logger.debug("Syncing slash commands...")

        if not SYNC_SLASH_COMMANDS:
            synced_commands = []
        elif IS_DEV:
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
            await ctx.send(f"{ctx.prefix}{ctx.invoked_with} {params}")
        elif isinstance(error, dc.CommandNotFound):
            await ctx.send(f'No command "{ctx.invoked_with}" ❌')
        elif isinstance(error, CancelCommand):
            pass
        else:
            await ctx.send(f"**{type(error).__name__}:** {error}")
