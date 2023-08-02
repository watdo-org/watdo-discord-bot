import asyncio
from typing import TYPE_CHECKING, Any, Dict, Callable, Awaitable, List
import discord
from discord.ext import commands as dc
from watdo.database import Database

if TYPE_CHECKING:
    from watdo.discord import Bot


class BaseCog(dc.Cog):
    def __init__(self, bot: "Bot", database: Database) -> None:
        self.bot = bot
        self.db = database

    @staticmethod
    def parse_params(command: dc.Command[Any, Any, Any]) -> str:
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

            if t in ("int", "float"):
                t = "number"

            t = f"*{t}*"
            p = param.name if t == "*str*" else f"{param.name}: {t}"
            p = p.replace("_", " ")

            if param.required:
                p = f"**[{p}]**"
            else:
                p = f"[{p}]"

            params.append(p)

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
