import time
import asyncio
from uuid import uuid4
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Sequence,
    Any,
    List,
    Optional,
    Dict,
    Callable,
    Awaitable,
)
import discord
from discord.ext import commands as dc
from watdo.models import Profile
from watdo.errors import CancelCommand
from watdo.database import Database
from watdo.safe_data import UTCOffset

if TYPE_CHECKING:
    from watdo.discord import Bot


@dataclass(kw_only=True)
class ParsedCommandParam:
    value: str
    is_required: bool
    description: Optional[str]


class BaseCog(dc.Cog):
    def __init__(self, bot: "Bot", database: Database) -> None:
        self.bot = bot
        self.db = database

    @staticmethod
    def parse_params_list(
        command: dc.Command[Any, Any, Any]
    ) -> List[ParsedCommandParam]:
        params = []

        for param in command.clean_params.values():
            if "[" in str(param.annotation):
                t = str(param.annotation)
            else:
                t = param.annotation.__name__

            if "typing.Optional[" in t:
                t = str(t).lstrip("typing.Optional[").rstrip("]")

            if t == "bool":
                t = "yes/no"

            if t == "Message":
                t = "message link/id"

            if t in ("int", "float"):
                t = "number"

            t = f"*{t}*"
            p = param.name if t == "*str*" else f"{param.name}: {t}"
            p = p.replace("_", " ")

            if param.required:
                p = f"**[{p}]**"
            else:
                p = f"[{p}]"

            params.append(
                ParsedCommandParam(
                    value=p,
                    is_required=param.required,
                    description=param.description,
                )
            )

        return params

    @staticmethod
    def parse_params(command: dc.Command[Any, Any, Any]) -> str:
        params = [p.value for p in BaseCog.parse_params_list(command)]
        return " ".join(params)

    async def add_reactions(
        self, message: discord.Message, emojis: Sequence[str]
    ) -> None:
        tasks = []

        for emoji in emojis:
            tasks.append(message.add_reaction(emoji))

        await asyncio.gather(*tasks)

    async def wait_for_confirmation(
        self,
        ctx: dc.Context["Bot"],
        message: discord.Message,
        *,
        raise_error: bool = False,
    ) -> bool:
        buttons = ("✅", "❌")

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            if user.id == ctx.author.id:
                if reaction.message.id == message.id:
                    if str(reaction) in buttons:
                        return True

            return False

        self.bot.loop.create_task(self.add_reactions(message, buttons))

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", check=check, timeout=60
            )
            reaction = str(reaction)
        except asyncio.TimeoutError:
            if raise_error:
                raise CancelCommand()

            return False

        if reaction == buttons[0]:
            return True

        if raise_error:
            raise CancelCommand()

        return False

    async def interview(
        self,
        ctx: dc.Context["Bot"],
        *,
        questions: Dict[str, Callable[[discord.Message], Awaitable[Any]]],
    ) -> List[Any]:
        def check(m: discord.Message) -> bool:
            if m.channel.id == ctx.channel.id:
                if m.author.id == ctx.author.id:
                    return True

            return False

        async def ask(question: str) -> Any:
            message = await self.bot.wait_for("message", check=check)
            return await questions[question](message)

        answers = []
        keys = list(questions.keys())
        bot_msg = await ctx.reply(keys[0])

        for index, question in enumerate(keys):
            if index != 0:
                await bot_msg.edit(content=question)

            while (answer := await ask(question)) is None:
                pass

            answers.append(answer)

        return answers

    async def _validate_utc_offset(self, message: discord.Message) -> Optional[float]:
        try:
            return UTCOffset(float(message.content)).value
        except Exception:
            await message.reply(
                "Please only send a number between -24 and 24.\n"
                "Example: `8` for UTC+8."
            )
            return None

    async def get_profile(self, ctx: dc.Context["Bot"]) -> Profile:
        profile = await Profile.from_channel_id(self.db, ctx.channel.id)

        if profile is None:
            message = await ctx.send("Current channel has no profile. Create one?")
            await self.wait_for_confirmation(ctx, message, raise_error=True)

            utc_offset = (
                await self.interview(
                    ctx,
                    questions={
                        "What is the UTC offset of this profile?": self._validate_utc_offset,
                    },
                )
            )[0]
            profile = Profile(
                utc_offset=utc_offset,
                uuid=uuid4().hex,
                created_at=time.time(),
                created_by=ctx.author.id,
            )
            self.bot.loop.create_task(profile.save(self.db))
            self.bot.loop.create_task(profile.add_to_channel(self.db, ctx.channel.id))

        return profile
