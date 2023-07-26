from discord.ext import commands as dc
from app.discord import Bot
from app.database import Database


class BaseCog(dc.Cog):
    def __init__(self, bot: Bot, database: Database) -> None:
        self.bot = bot
        self.db = database
