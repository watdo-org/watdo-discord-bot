from discord.ext import commands as dc
from app.discord import Bot
from app.database import Database


class BaseCog(dc.Cog):
    def __init__(self, bot: Bot, database: Database) -> None:
        self.bot = bot
        self.db = database

    # async def interview(
    #     self,
    #     ctx: dc.Context,
    #     *,
    #     questions: Dict[str, InitLaterCallback[Any]],
    # ) -> List[Any]:
    #     def check(m: discord.Message) -> bool:
    #         if m.channel.id == ctx.channel.id:
    #             if m.author.id == ctx.author.id:
    #                 return True

    #         return False

    #     answers = []
    #     keys = list(questions.keys())
    #     bot_msg = await ctx.reply(keys[0])

    #     for index, q in enumerate(keys):
    #         if index != 0:
    #             await bot_msg.edit(content=q)

    #         msg = await self.bot.wait_for("message", check=check)
    #         answer = questions[q](msg.content)
    #         answers.append(answer)

    #     return answers

    @staticmethod
    def parse_params(command: dc.Command) -> str:
        params = []

        for param in command.clean_params.values():
            t = param.annotation

            if t is bool:
                t = "yes/no"

            if t in (int, float):
                t = "number"

            if "typing.Optional[" in str(t):
                t = str(t).lstrip("typing.Optional[").rstrip("]")

            t = f"*{t}*"
            p = param.name if param.annotation is str else f"{param.name}: {t}"
            p = p.replace("_", " ")

            if param.required:
                p = f"**[{p}]**"
            else:
                p = f"[{p}]"

            params.append(p)

        return " ".join(params)
