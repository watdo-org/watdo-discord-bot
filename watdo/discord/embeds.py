import logging
from typing import TYPE_CHECKING, Any
import discord
from watdo import dt
from watdo.models import Profile

if TYPE_CHECKING:
    from watdo.discord import Bot


class Embed(discord.Embed):
    def __init__(self, bot: "Bot", title: str, **kwargs: Any) -> None:
        if kwargs.get("color") is None:
            kwargs["color"] = bot.color

        super().__init__(title=title, **kwargs)


class ErrorEmbed(discord.Embed):
    def __init__(self, record: logging.LogRecord, **kwargs: Any) -> None:
        super().__init__(
            title=record.levelname,
            description=f"**{record.name}** in module `{record.pathname}` at line **{record.lineno}**",
            color=discord.Colour.from_rgb(255, 8, 8),
            **kwargs,
        )
        self.add_field(
            name="Message",
            value=f"```{record.message[max(0, len(record.message) - 1018):]}```",
        )
        self.set_footer(text=record.asctime)


class ProfileEmbed(Embed):
    def __init__(self, bot: "Bot", profile: Profile) -> None:
        super().__init__(
            bot,
            "PROFILE",
            timestamp=dt.fromtimestamp(
                profile.created_at.value, profile.utc_offset.value
            ),
        )

        user = bot.get_user(profile.created_by.value)

        if user is not None:
            self.set_author(name=user.display_name, icon_url=user.display_avatar.url)

        utc = str(profile.utc_offset.value).rstrip("0").rstrip(".")

        if utc[0] != "-":
            utc = f"+{utc}"

        self.add_field(name="Timezone", value=f"UTC{utc}")
        self.add_field(name="ID", value=profile.uuid.value, inline=False)
