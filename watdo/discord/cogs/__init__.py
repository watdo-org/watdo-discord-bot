import time
import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Callable, Awaitable, List, Optional
import discord
from discord.ext import commands as dc
from watdo.models import User, Task
from watdo.database import Database
from watdo.safe_data import UTCOffsetHour

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

            if t.is_recurring:
                task_type = "🔁" if t.has_reminder.value else "🔁 🔕"
            elif t.due_date:
                task_type = "🔔" if t.has_reminder.value else "🔕"

            if t.is_done:
                status = "✅ "
            elif t.is_overdue:
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

    async def wait_for_confirmation(
        self, ctx: dc.Context["Bot"], message: discord.Message
    ) -> bool:
        buttons = ("✅", "❌")

        def check(reaction: discord.Reaction, user: discord.User) -> bool:
            if user.id == ctx.author.id:
                if reaction.message.id == message.id:
                    if str(reaction) in buttons:
                        return True

            return False

        for button in buttons:
            self.bot.loop.create_task(message.add_reaction(button))

        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add", check=check, timeout=60
            )
            reaction = str(reaction)
        except asyncio.TimeoutError:
            return False

        if reaction == buttons[0]:
            return True

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
            return UTCOffsetHour(float(message.content)).value
        except Exception:
            await message.reply(
                "Please only send a number between -24 and 24.\n"
                "Example: `8` for UTC+8."
            )
            return None

    async def get_user_data(self, ctx: dc.Context["Bot"]) -> User:
        uid = str(ctx.author.id)
        user = await self.db.get_user_data(uid)

        if user is None:
            utc_offset = (
                await self.interview(
                    ctx,
                    questions={
                        "What is your UTC offset?": self._validate_utc_offset,
                    },
                )
            )[0]
            user = User(utc_offset_hour=utc_offset, created_at=time.time())
            await self.db.set_user_data(uid, user)

        return user
