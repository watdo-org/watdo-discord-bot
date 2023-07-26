import discord
from app.discord import Bot


class Embed(discord.Embed):
    def __init__(self, bot: Bot, title: str) -> None:
        super().__init__(title=title, color=bot.color)
        self.set_author(name="watdo", icon_url=bot.user.display_avatar.url)
