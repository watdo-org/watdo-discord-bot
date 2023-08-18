from typing import Dict
from discord.ext import commands as dc
from watdo.discord import Bot
from watdo.discord.cogs import BaseCog


class Tasks(BaseCog):
    pass


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tasks(bot, bot.db))
