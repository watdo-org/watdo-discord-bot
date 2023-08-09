import codecs
import asyncio
import logging
from typing import (
    TYPE_CHECKING,
    cast,
    Any,
    Dict,
    Optional,
    List,
    Awaitable,
    Callable,
    Iterator,
)
import discord
from discord.ext import commands as dc
from watdo import dt
from watdo.models import Task

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


class TaskEmbed(Embed):
    def __init__(self, bot: "Bot", task: Task) -> None:
        if task.is_done:
            color = discord.Colour.from_rgb(65, 161, 69)
            icon_url = (
                "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/"
                "Eo_circle_green_checkmark.svg/800px-Eo_circle_green_checkmark.svg.png"
            )
        elif task.is_overdue:
            color = discord.Colour.from_rgb(255, 192, 72)
            icon_url = "https://cdn-icons-png.flaticon.com/512/6897/6897039.png"
        else:
            color = None
            icon_url = None

        if task.description is None:
            description = None
        else:
            desc_bytes = bytes(task.description.value, "utf-8")
            desc_escaped = codecs.escape_decode(desc_bytes)[0]
            description = cast(bytes, desc_escaped).decode("utf-8").rstrip()

        super().__init__(bot, task.title.value, color=color, description=description)
        author = "📝"

        if task.is_recurring:
            author = "🔁" if task.has_reminder.value else "🔁 🔕"
        elif task.due_date:
            author = "🔔" if task.has_reminder.value else "🔕"

        self.set_author(
            name=f"{'📌 ' if task.is_important.value else ''}"
            f"{author} {task.category.value}",
            icon_url=icon_url,
        )

        date_format = "%b %d, %Y\n%I:%M %p"

        if task.due_date is not None:
            self.add_field(
                name="Due Date",
                value=f"{task.due_date.strftime(date_format)}",
            )

        if task.is_recurring:
            self.set_footer(text=task.rrulestr)

        self.add_field(
            name="Created",
            value=f"{task.date_created.strftime(date_format)}",
        )

        if task.last_done is not None:
            last_done_date = cast(dt.datetime, task.last_done_date)
            self.add_field(
                name="Last Done",
                value=f"{last_done_date.strftime(date_format)}",
            )


class PagedEmbed:
    def __init__(
        self,
        bot: "Bot",
        *,
        timeout: float = 60 * 60,  # 1 hour
        controls: Optional[Dict[str, str]] = None,
    ) -> None:
        if controls is None:
            controls = {
                "extract": "✴",
                "first": "\u23ee",
                "previous": "\u25c0",
                "next": "\u25b6",
                "last": "\u23ed",
            }

        self.bot = bot
        self.controls = controls
        self.timeout = timeout  # time before the pagination deletes itself
        self.pages: List[Embed] = []  # stores individual embeds
        self.current = 0

        self._message: discord.Message
        self._custom_buttons: Dict[str, Callable[[Embed], Awaitable[None]]] = {}

    def __iter__(self) -> Iterator[Embed]:
        """Make this object iterable."""
        return iter(self.pages)

    def __len__(self) -> int:
        """Return the number of pages."""
        return len(self.pages)

    def _set_page_numbers(self) -> None:
        for index, page in enumerate(self.pages):
            page_no = f"{index + 1}/{len(self.pages)}"

            if page.footer.text is None:
                page.set_footer(text=page_no)
            else:
                page.set_footer(text=f"{page_no} • {page.footer.text}")

    def send(self, ctx: dc.Context["Bot"]) -> None:
        self.bot.loop.create_task(self._send(ctx))

    async def _send(self, ctx: dc.Context["Bot"]) -> None:
        """Start and send the embeds paginating lorem."""
        self._set_page_numbers()

        embeds_len = 1
        message = await ctx.send(embeds=self.pages[0:embeds_len])
        self._message = message

        # add the control reactions
        for name, emoji in self.controls.items():
            ctx.bot.loop.create_task(message.add_reaction(emoji))

        for custom_reaction, custom_function in self._custom_buttons.items():
            ctx.bot.loop.create_task(message.add_reaction(custom_reaction))

        # always wait for user reaction until a certain timeout
        while True:
            try:
                reaction, user = await ctx.bot.wait_for(
                    "reaction_add",
                    check=lambda reaction, user: user.id == ctx.author.id,
                    timeout=self.timeout,
                )  # wait for reaction input

                # ensure that the reaction is in the same message
                if reaction.message.id == message.id:
                    reaction = str(reaction)
                else:
                    continue

            except asyncio.TimeoutError:
                break

            # ignore the reaction input if the reaction is from a bot
            if user.bot:
                continue

            if reaction == self.controls["first"]:
                # go to the first page
                self.current = 0
            elif reaction == self.controls["previous"]:
                # go to the previous page if there's any
                if self.current != 0:
                    self.current -= 1
            elif reaction == self.controls["next"]:
                # go to the next page if there's any
                if self.current != len(self) - 1:
                    self.current += 1
            elif reaction == self.controls["last"]:
                # go to the last page
                self.current = len(self) - 1
            elif reaction == self.controls["extract"]:
                embeds_len = 10 if embeds_len == 1 else 1
            elif reaction in self._custom_buttons:
                await self._custom_buttons[reaction](self.pages[self.current])

            ctx.bot.loop.create_task(
                message.edit(
                    embeds=self.pages[
                        self.current * embeds_len : self.current * embeds_len
                        + embeds_len
                    ],
                )
            )

    def add_button(
        self, reaction: str, function: Callable[[Embed], Awaitable[None]]
    ) -> None:
        self._custom_buttons[reaction] = function

    def add_pages(self, *pages: Embed) -> None:
        """Add pages."""
        for page in pages:
            self.pages.append(page)

    def add_page(self, page: Embed) -> None:
        """Add page."""
        self.pages.append(page)
