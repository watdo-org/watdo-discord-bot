import asyncio
import discord
from discord.ext import commands as dc
from watdo.database import Database


class Bot(dc.Bot):
    def __init__(self, *, loop: asyncio.AbstractEventLoop, database: Database) -> None:
        super().__init__(loop=loop, command_prefix="$", intents=discord.Intents.all())
        self.db = database
