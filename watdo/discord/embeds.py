import math
import logging
import asyncio
from typing import TYPE_CHECKING, cast, Any, Tuple, Callable, Awaitable
import discord
from discord.ext import commands as dc
from watdo import dt
from watdo.models import Profile, Task, ScheduledTask

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


class TaskEmbed(Embed):
    def __init__(self, bot: "Bot", task: Task, *, is_simple: bool = False) -> None:
        if task.is_done:
            color = discord.Colour.from_rgb(65, 161, 69)
            icon_url = (
                "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/"
                "Eo_circle_green_checkmark.svg/800px-Eo_circle_green_checkmark.svg.png"
            )
        elif isinstance(task, ScheduledTask) and task.is_overdue:
            color = discord.Colour.from_rgb(255, 192, 72)
            icon_url = "https://cdn-icons-png.flaticon.com/512/6897/6897039.png"
        else:
            color = None
            icon_url = None

        if task.description is None:
            description = None
        else:
            description = task.description.escaped

        super().__init__(bot, task.title.value, color=color, description=description)
        author = "📝"

        if isinstance(task, ScheduledTask):
            if task.is_recurring:
                author = "🔁" if task.has_reminder.value else "🔁 🔕"
            elif task.due_date:
                author = "🔔" if task.has_reminder.value else "🔕"

        self.set_author(
            name=f"{'📌 ' if task.importance.value else ''}"
            f"{author} {task.category.value}",
            icon_url=icon_url,
        )

        if not is_simple:
            date_format = "%b %d, %Y\n%I:%M %p"

            if isinstance(task, ScheduledTask):
                self.add_field(
                    name="Due Date",
                    value=f"{task.due_date.strftime(date_format)}",
                )

                if task.is_recurring:
                    self.set_footer(text=task.rrulestr)

            if task.last_done is not None:
                last_done_date = cast(dt.datetime, task.last_done_date)
                self.add_field(
                    name="Last Done",
                    value=f"{last_done_date.strftime(date_format)}",
                )

            self.add_field(
                name="Created At",
                value=f"{task.date_created.strftime(date_format)}",
            )

            created_by = bot.get_user(task.created_by.value)

            if created_by is not None:
                self.add_field(name="Created By", value=created_by.mention)


class PagedEmbed:
    def __init__(
        self,
        ctx: dc.Context["Bot"],
        embeds_getter: Callable[[], Awaitable[Tuple[discord.Embed, ...]]],
        *,
        timeout: float = 60 * 60,  # 1 hour
        empty_message: str = "No items.",
    ) -> None:
        self.ctx = ctx
        self.embeds_getter = embeds_getter
        self.timeout = timeout
        self.empty_message = Embed(ctx.bot, empty_message)

        self.current_page = 0
        self.embeds_len = 1

        self.message: discord.Message
        self.embeds: Tuple[discord.Embed, ...]

        self._controls = {
            "extract": "✴",
            "first": "\u23ee",
            "previous": "\u25c0",
            "next": "\u25b6",
            "last": "\u23ed",
            "refresh": "🔄",
        }

    async def update_embeds(self) -> None:
        self.embeds = await self.embeds_getter()
        self._set_embeds_footer()

    def _set_embeds_footer(self) -> None:
        for index, embed in enumerate(self.embeds):
            page_no = f"{index + 1}/{len(self.embeds)}"

            if embed.footer.text is None:
                embed.set_footer(text=page_no)
            else:
                embed.set_footer(text=f"{page_no} • {embed.footer.text}")

    def _get_last_page_index(self) -> int:
        try:
            current = (len(self.embeds) - 1) % (len(self.embeds) / self.embeds_len)
            return math.ceil(current)
        except ZeroDivisionError:
            return 0

    def _process_reaction(self, reaction: str, user: discord.User) -> None:
        embeds = self.embeds

        if len(embeds) == 0:
            pass
        elif reaction == self._controls["first"]:
            self.current_page = 0
        elif reaction == self._controls["previous"]:
            if self.current_page != 0:
                self.current_page -= 1
        elif reaction == self._controls["next"]:
            if self.current_page != len(embeds) - 1:
                self.current_page += 1
        elif reaction == self._controls["last"]:
            self.current_page = self._get_last_page_index()
        elif reaction == self._controls["extract"]:
            self.embeds_len = 10 if self.embeds_len == 1 else 1
        elif reaction == self._controls["refresh"]:
            pass

        embeds = embeds[
            self.current_page * self.embeds_len : self.current_page * self.embeds_len
            + self.embeds_len
        ]

        if len(embeds) == 0:
            self.current_page = self._get_last_page_index()
            embeds = embeds[
                self.current_page
                * self.embeds_len : self.current_page
                * self.embeds_len
                + self.embeds_len
            ]

        self.ctx.bot.loop.create_task(
            self.message.edit(embeds=embeds or [self.empty_message])
        )
        self.ctx.bot.loop.create_task(
            self.ctx.bot.remove_reaction(
                self.message,
                reaction=reaction,
                user=user,
            )
        )

    async def _start_loop(self) -> None:
        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            return (user.id == self.ctx.author.id) and (
                reaction.message.id == self.message.id
            )

        while True:
            try:
                reaction, user = await self.ctx.bot.wait_for(
                    "reaction_add", check=check, timeout=self.timeout
                )
            except asyncio.TimeoutError:
                break

            await self.update_embeds()
            self._process_reaction(str(reaction), user)

    async def send(self) -> discord.Message:
        from watdo.discord.cogs import BaseCog

        await self.update_embeds()
        self.message = await BaseCog.send(
            self.ctx,
            embeds=self.embeds[self.current_page : self.embeds_len]
            or [self.empty_message],
        )

        for emoji in self._controls.values():
            self.ctx.bot.loop.create_task(self.message.add_reaction(emoji))

        self.ctx.bot.loop.create_task(self._start_loop())
        return self.message
