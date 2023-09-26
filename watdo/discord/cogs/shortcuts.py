from typing import List
from discord.ext import commands as dc
from watdo.errors import CancelCommand
from watdo.discord import Bot
from watdo.discord.cogs import BaseCog


class Shortcuts(BaseCog, description="Speed up your workflow with command shortcuts."):
    @dc.hybrid_command()  # type: ignore[arg-type]
    async def set_short(self, ctx: dc.Context[Bot], name: str) -> None:
        """Set a command shortcut."""
        command: List[str] = []

        while True:
            if len(command) == 0:
                question = (
                    f"Type in the command to be executed when **{name}** is sent.\n"
                    "To finish, type **DONE** or **CANCEL**."
                )
            else:
                question = "Another command:"

            inputs = await self.interview(ctx, questions={question: None})
            inp = inputs[0]

            if inp == "DONE":
                if len(command) == 0:
                    await BaseCog.send(ctx, "Please put at least one command.")
                    continue

                break

            if inp == "CANCEL":
                raise CancelCommand()

            command.append(inp)

        await self.db.set_command_shortcut(str(ctx.author.id), name, command)

        cs = "".join(f"```\n{c}\n```" for c in command)
        await BaseCog.send(ctx, f"Command shortcut set ✅\n**{name}**\n{cs}")

    @dc.hybrid_command()  # type: ignore[arg-type]
    async def shorts(self, ctx: dc.Context[Bot]) -> None:
        """Show all your command shortcuts."""
        data = await self.db.get_all_command_shortcuts(str(ctx.author.id))
        message = []

        for name, command in data.items():
            cs = "".join(f"```\n{c}\n```" for c in command)
            message.append(f"**{name}**\n{cs}")

        await BaseCog.send(ctx, "\n".join(message) or "No command shortcuts ❌")

    @dc.hybrid_command()  # type: ignore[arg-type]
    async def delete_short(self, ctx: dc.Context[Bot], name: str) -> None:
        """Delete a command shortcut."""
        deleted_count = await self.db.delete_command_shortcut(str(ctx.author.id), name)

        if deleted_count > 0:
            await BaseCog.send(ctx, "Deleted ✅")
        else:
            await BaseCog.send(ctx, f'Command shortcut "{name}" not found ❌')


async def setup(bot: Bot) -> None:
    await bot.add_cog(Shortcuts(bot, bot.db))
