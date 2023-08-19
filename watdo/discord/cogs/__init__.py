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
    Mapping,
)
import discord
from discord.ext import commands as dc
from watdo.models import Profile, Task, ScheduledTask
from watdo.errors import CancelCommand
from watdo.database import Database
from watdo.safe_data import UTCOffset
from watdo.discord.embeds import ProfileEmbed

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
    def tasks_to_text(tasks: List[Task], *, no_category: bool = False) -> str:
        res = []

        for i, t in enumerate(tasks):
            task_type = "📝"
            status = ""

            if isinstance(t, ScheduledTask):
                if t.is_recurring:
                    task_type = "🔁" if t.has_reminder.value else "🔁 🔕"
                elif t.due_date:
                    task_type = "🔔" if t.has_reminder.value else "🔕"

            if t.is_done:
                status = "✅ "
            elif isinstance(t, ScheduledTask) and t.is_overdue:
                status = "⚠️ "

            p = (
                f"{status}{'📌 ' if t.is_important.value else ''}"
                f'{task_type}{"" if no_category else f" [{t.category.value}]"}'
            )
            res.append(f"{i + 1}. {p} {t.title.value}")

        return "\n".join(res)

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

    def _edit_choices(
        self,
        message: discord.Message,
        mapping: Dict[str, str],
        *,
        choice: Optional[str] = None,
    ) -> None:
        choices = []

        for emoji, text in mapping.items():
            if emoji == choice:
                text = f"__**{text}**__"

            choices.append(f"- {emoji}   {text}")

        c = "\n".join(choices)
        self.bot.loop.create_task(message.edit(content=f"{message.content}\n{c}"))

    async def wait_for_choice(
        self,
        ctx: dc.Context["Bot"],
        message: discord.Message,
        *,
        mapping: Dict[str, str],
        default: str,
    ) -> str:
        emojis = tuple(mapping.keys())

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            if user.id == ctx.author.id:
                if reaction.message.id == message.id:
                    if str(reaction) in emojis:
                        return True

            return False

        self._edit_choices(message, mapping)
        self.bot.loop.create_task(self.add_reactions(message, emojis))

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", check=check, timeout=60
            )
            reaction = str(reaction)
            self._edit_choices(message, mapping, choice=reaction)
            return reaction
        except asyncio.TimeoutError:
            self._edit_choices(message, mapping, choice=default)
            return default

    async def interview(
        self,
        ctx: dc.Context["Bot"],
        *,
        questions: Mapping[
            str,
            None | Callable[[discord.Message], Awaitable[Any]],
        ],
    ) -> List[Any]:
        def check(m: discord.Message) -> bool:
            if m.channel.id == ctx.channel.id:
                if m.author.id == ctx.author.id:
                    return True

            return False

        async def ask(question: str) -> Any:
            try:
                message = await self.bot.wait_for(
                    "message", check=check, timeout=60 * 5
                )
            except asyncio.TimeoutError:
                raise CancelCommand()

            validator = questions[question]

            if validator is None:
                return message.content

            return await validator(message)

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
            message = await ctx.send(
                "Current channel has no profile. What would you like to do?"
            )
            reaction = await self.wait_for_choice(
                ctx,
                message,
                mapping={
                    "♻️": "Add this channel to an existing profile",
                    "✅": "Create a new profile for this channel",
                    "❌": "Cancel",
                },
                default="❌",
            )

            if reaction == "❌":
                raise CancelCommand()

            if reaction == "♻️":
                questions = {"What is the ID of the profile?": None}
                profile_id = (await self.interview(ctx, questions=questions))[0]
                profile = await Profile.from_id(self.db, profile_id)

                if profile is None:
                    await ctx.send("Profile not found ❌")
                    raise CancelCommand()

                if profile.created_by.value != ctx.author.id:
                    await ctx.send("You don't own that profile ❌")
                    raise CancelCommand()

                await profile.add_channel(ctx.channel.id)
                await ctx.send(f"Channel added to profile `{profile_id}` ✅")
                return await self.get_profile(ctx)

            utc_offset = (
                await self.interview(
                    ctx,
                    questions={
                        "What is the UTC offset of this profile?": self._validate_utc_offset,
                    },
                )
            )[0]
            profile = Profile(
                self.db,
                utc_offset=utc_offset,
                uuid=uuid4().hex,
                created_at=time.time(),
                created_by=ctx.author.id,
                channel_id=ctx.channel.id,
            )
            self.bot.loop.create_task(profile.save())
            self.bot.loop.create_task(profile.add_channel(ctx.channel.id))
            await ctx.send(
                "New profile created ✅", embed=ProfileEmbed(self.bot, profile)
            )

        return profile
