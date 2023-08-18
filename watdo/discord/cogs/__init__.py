from discord.ext import commands as dc
from watdo.discord import Bot
from watdo.database import Database


class BaseCog(dc.Cog):
    def __init__(self, bot: Bot, database: Database) -> None:
        self.bot = bot
        self.db = database
