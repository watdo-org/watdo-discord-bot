import asyncio
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    List,
    Awaitable,
    Callable,
    Iterator,
)
import humanize
import discord
from discord.ext import commands as dc
from app.models import Task

if TYPE_CHECKING:
    from app.discord import Bot


class Embed(discord.Embed):
    def __init__(self, bot: "Bot", title: str, **kwargs: Any) -> None:
        super().__init__(title=title, color=bot.color, **kwargs)


class TaskEmbed(Embed):
    def __init__(self, bot: "Bot", task: Task) -> None:
        super().__init__(bot, task.title.value, timestamp=task.due_date)
        author = "📝"

        if task.is_recurring:
            author = "🔁"
        elif task.due_date:
            author = "🔔"

        self.set_author(
            name=f"{'📌 ' if task.is_important.value else ''}"
            f"{author} {task.category.value}",
            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/"
            "Eo_circle_green_checkmark.svg/800px-Eo_circle_green_checkmark.svg.png"
            if task.is_done
            else None,
        )
        self.add_field(
            name="Created",
            value=f"{humanize.naturaldate(task.date_created).capitalize()} "
            f"({humanize.naturaltime(task.date_created)})",
        )

        if task.last_done is not None:
            self.add_field(
                name="Last Done",
                value=f"{humanize.naturaldate(task.last_done_date).capitalize()} "
                f"({humanize.naturaltime(task.last_done_date)})",
            )


class PagedEmbed:
    def __init__(
        self,
        bot: "Bot",
        *,
        timeout: float = 300,
        controls: Optional[Dict[str, str]] = None,
    ) -> None:
        if controls is None:
            controls = {
                "first": "\u23ee",
                "previous": "\u25c0",
                "next": "\u25b6",
                "last": "\u23ed",
                "extract": "✴",
            }

        self.bot = bot
        self.controls = controls
        self.timeout = timeout  # time before the pagination deletes itself
        self.pages: List[Embed] = []  # stores individual embeds
        self.current = 0

        self._message: discord.Message
        self._custom_buttons: Dict[str, Callable[[Embed], Awaitable[None]]] = {}

    def __getitem__(self, index: int) -> Embed:
        """Enable indexing to this object."""
        return self.pages[index]

    def __iter__(self) -> Iterator[Embed]:
        """Make this object iterable."""
        return iter(self.pages)

    def __len__(self) -> int:
        """Return the number of pages."""
        return len(self.pages)

    def _set_page_numbers(self) -> None:
        for index, page in enumerate(self.pages):
            page.set_footer(text=f"{index + 1}/{len(self.pages)}")

    def send(self, ctx: dc.Context) -> None:
        self.bot.loop.create_task(self._send(ctx))

    async def _send(self, ctx: dc.Context) -> None:
        """Start and send the embeds paginating lorem."""
        self._set_page_numbers()

        message = await ctx.send(embed=self[0])
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
                ctx.bot.loop.create_task(message.edit(embeds=self.pages))
                break
            elif reaction in self._custom_buttons:
                await self._custom_buttons[reaction](self.pages[self.current])

            ctx.bot.loop.create_task(message.edit(embed=self.pages[self.current]))

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

    def set_thumbnail(self, **kwargs: Any) -> None:
        """Set thumbnail of all pages."""
        for page in self:
            page.set_thumbnail(**kwargs)

    def set_footer(self, **kwargs: Any) -> None:
        """Set footer of all pages."""
        for page in self:
            page.set_footer(**kwargs)

    def set_image(self, **kwargs: Any) -> None:
        """Set an image for all pages."""
        for page in self:
            page.set_image(**kwargs)

    async def set_current_page(self, page: Embed) -> None:
        self.pages[self.current] = page
        await self._message.edit(embed=self.pages[self.current])
