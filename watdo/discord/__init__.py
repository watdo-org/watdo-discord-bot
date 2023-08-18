import asyncio
import discord
from discord.ext import commands as dc


class Bot(dc.Bot):
    def __init__(self, *, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__(loop=loop, command_prefix="$", intents=discord.Intents.all())
