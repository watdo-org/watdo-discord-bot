import time
from uuid import uuid4
from typing import Dict, Optional, Tuple, Sequence, Callable, Awaitable
import recurrent
import dateparser
import discord
from discord.ext import commands as dc
from watdo import dt
from watdo.errors import CancelCommand
from watdo.models import Profile, Task, ScheduledTask, DueT
from watdo.safe_data import Timestamp
from watdo.collections import TasksCollection
from watdo.discord import Bot
from watdo.discord.cogs import BaseCog
from watdo.discord.embeds import Embed, TaskEmbed, PagedEmbed


class Tasks(BaseCog):
    @dc.hybrid_command()  # type: ignore[arg-type]
    async def summary(self, ctx: dc.Context[Bot]) -> None:
        """Show the summary of all your tasks."""
        profile = await self.get_profile(ctx)
        tasks = await Task.get_tasks_of_profile(self.db, profile)

        embed = Embed(self.bot, "TASKS SUMMARY")

        total = 0
        is_important = 0
        overdue = 0
        recurring = 0
        one_time = 0
        done = 0
        max_categ_len = 0
        categories: Dict[str, int] = {}

        for task in tasks:
            total += 1

            if task.importance.value:
                is_important += 1

            if isinstance(task, ScheduledTask):
                if task.is_overdue:
                    overdue += 1

            if isinstance(task, ScheduledTask) and task.is_recurring:
                recurring += 1
            else:
                one_time += 1

            if task.is_done:
                done += 1

            if len(task.category.value) > max_categ_len:
                max_categ_len = len(task.category.value)

            try:
                categories[task.category.value] += 1
            except KeyError:
                categories[task.category.value] = 1

        embed.add_field(name="Total", value=total)
        embed.add_field(name="Important", value=is_important)
        embed.add_field(name="Overdue", value=overdue)
        embed.add_field(name="Recurring", value=recurring)
        embed.add_field(name="One-Time", value=one_time)
        embed.add_field(name="Done", value=done)

        if categories:
            c = "\n".join(
                f"{k.ljust(max_categ_len)}  {v}" for k, v in categories.items()
            )
            embed.add_field(
                name="Categories", value=f"```\n{c[:1000]}\n```", inline=False
            )

        await BaseCog.send(ctx, embed=embed)

    async def _send_tasks(
        self,
        ctx: dc.Context[Bot],
        tasks_getter: Callable[[], Awaitable[Sequence[Task]]],
        *,
        as_text: bool,
        is_simple: bool = False,
    ) -> None:
        async def embeds_getter() -> Tuple[discord.Embed, ...]:
            return tuple(
                TaskEmbed(self.bot, task, is_simple=is_simple)
                for task in await tasks_getter()
            )

        if as_text:
            tasks = await tasks_getter()

            if not tasks:
                await BaseCog.send(ctx, "No tasks.")
                return

            await BaseCog.send(ctx, self.tasks_to_text(tasks))
            return

        paged_embed = PagedEmbed(ctx, embeds_getter)
        await paged_embed.send()

    @dc.hybrid_command()  # type: ignore[arg-type]
    async def list(
        self,
        ctx: dc.Context[Bot],
        category: Optional[str] = None,
        as_text: bool = False,
    ) -> None:
        """Show your tasks list."""

        async def tasks_getter() -> Sequence[Task]:
            tasks = await Task.get_tasks_of_profile(
                self.db, profile, category=category or None
            )
            tasks.sort_by_priority()
            return tasks.items

        profile = await self.get_profile(ctx)
        await self._send_tasks(ctx, tasks_getter, as_text=as_text)

    def _parse_due(self, ctx: dc.Context[Bot], due: str, utc_offset: float) -> DueT:
        tz = dt.utc_offset_to_tz(utc_offset)
        date = dateparser.parse(
            due,
            settings={
                "RETURN_AS_TIMEZONE_AWARE": True,
                "TIMEZONE": tz.tzname(dt.date_now(utc_offset)) or "",
            },
        )

        if date is not None:
            return date.timestamp()  # type: ignore[return-value]

        rr: Optional[str | dt.datetime] = recurrent.parse(
            due,
            now=dt.date_now(utc_offset),
        )

        if isinstance(rr, str):
            if "DTSTART:" not in rr:
                date_now = dt.date_now(utc_offset)
                d = date_now.strftime("%Y%m%dT%H%M%S")
                rr = f"DTSTART:{d}\n{rr}"

            return rr  # type: ignore[return-value]

        if isinstance(rr, dt.datetime_type):
            return rr.timestamp()  # type: ignore[return-value]

        self.bot.loop.create_task(BaseCog.send(ctx, f"Failed to parse `{due}`"))
        raise CancelCommand()

    async def _update_task(
        self,
        ctx: dc.Context[Bot],
        profile: Profile,
        existing_task: Task,
        *,
        title: str,
        category: str,
        importance: float,
        energy: float,
        due: Optional[str],
        description: Optional[str],
        has_reminder: bool,
        is_auto_done: bool,
    ) -> None:
        if due is None:
            task = Task(
                # Copy from existing task
                existing_task.db,
                profile=existing_task.profile,
                profile_id=existing_task.profile_id.value,
                last_done=existing_task.last_done.value
                if existing_task.last_done
                else None,
                uuid=existing_task.uuid.value,
                created_at=existing_task.created_at.value,
                created_by=existing_task.created_by.value,
                channel_id=ctx.channel.id,
                #
                # From user input
                title=title,
                category=category,
                importance=importance,
                energy=energy,
                description=description,
            )
        else:
            task = ScheduledTask(
                # Copy from existing task
                existing_task.db,
                profile=existing_task.profile,
                profile_id=existing_task.profile_id.value,
                last_done=existing_task.last_done.value
                if existing_task.last_done
                else None,
                uuid=existing_task.uuid.value,
                created_at=existing_task.created_at.value,
                created_by=existing_task.created_by.value,
                channel_id=ctx.channel.id,
                #
                # From user input
                title=title,
                category=category,
                importance=importance,
                energy=energy,
                due=self._parse_due(ctx, due, profile.utc_offset.value),
                description=description,
                has_reminder=has_reminder,
                is_auto_done=is_auto_done,
            )

            task.next_reminder = Timestamp(task.due_date.timestamp())

        await task.save()
        await BaseCog.send(ctx, "Task updated ✅", embed=TaskEmbed(self.bot, task))

    async def _add_task(
        self,
        ctx: dc.Context[Bot],
        profile: Profile,
        *,
        title: str,
        category: str,
        importance: float,
        energy: float,
        due: Optional[str],
        description: Optional[str],
        has_reminder: bool,
        is_auto_done: bool,
    ) -> None:
        if due is None:
            task = Task(
                self.db,
                profile=profile,
                profile_id=profile.uuid.value,
                last_done=None,
                uuid=uuid4().hex,
                created_at=time.time(),
                created_by=ctx.author.id,
                channel_id=ctx.channel.id,
                #
                # From user input
                title=title,
                category=category,
                importance=importance,
                energy=energy,
                description=description,
            )
        else:
            task = ScheduledTask(
                self.db,
                profile=profile,
                profile_id=profile.uuid.value,
                last_done=None,
                uuid=uuid4().hex,
                created_at=time.time(),
                created_by=ctx.author.id,
                channel_id=ctx.channel.id,
                #
                # From user input
                title=title,
                category=category,
                importance=importance,
                energy=energy,
                due=self._parse_due(ctx, due, profile.utc_offset.value),
                description=description,
                has_reminder=has_reminder,
                is_auto_done=is_auto_done,
            )

            task.next_reminder = Timestamp(task.due_date.timestamp())

        await task.save()
        await BaseCog.send(ctx, "Task added ✅", embed=TaskEmbed(self.bot, task))

    @dc.hybrid_command()  # type: ignore[arg-type]
    async def todo(
        self,
        ctx: dc.Context[Bot],
        title: str,
        category: str,
        importance: float,
        energy: float,
        due: Optional[str] = dc.parameter(
            default=None,
            description='**Examples:**\n"tomorrow at 5PM"\n"every morning"\n"in 3 hours"',
        ),
        description: Optional[str] = None,
        has_reminder: bool = True,
        is_auto_done: bool = False,
    ) -> None:
        """Add a task to do.
        **Use this please: https://nietsuu.github.io/watdo**
        If the title is a duplicate, the old task will be overwritten."""

        if due == "":
            due = None

        profile = await self.get_profile(ctx)
        existing_task = await Task.from_title(self.db, profile, title)

        if existing_task is not None:
            await self._update_task(
                ctx,
                profile,
                existing_task,
                title=title,
                category=category,
                importance=importance,
                energy=energy,
                due=due,
                description=description,
                has_reminder=has_reminder,
                is_auto_done=is_auto_done,
            )
        else:
            await self._add_task(
                ctx,
                profile,
                title=title,
                category=category,
                importance=importance,
                energy=energy,
                due=due,
                description=description,
                has_reminder=has_reminder,
                is_auto_done=is_auto_done,
            )

    async def _get_do_tasks(
        self,
        ctx: dc.Context[Bot],
        category: Optional[str] = None,
    ) -> TasksCollection:
        profile = await self.get_profile(ctx)
        tasks = await Task.get_tasks_of_profile(
            self.db,
            profile,
            category=category or None,
            ignore_done=True,
        )
        return tasks

    @dc.hybrid_command(aliases=["do"])  # type: ignore[arg-type]
    async def do_priority(
        self,
        ctx: dc.Context[Bot],
        category: Optional[str] = None,
        as_text: bool = False,
    ) -> None:
        """Show priority tasks."""

        async def tasks_getter() -> Sequence[Task]:
            tasks = await self._get_do_tasks(ctx, category)
            tasks.sort_by_priority()
            return tasks.items

        await self._send_tasks(ctx, tasks_getter, as_text=as_text, is_simple=True)

    @dc.hybrid_command(aliases=["dailies"])  # type: ignore[arg-type]
    async def do_dailies(
        self,
        ctx: dc.Context[Bot],
        category: Optional[str] = None,
        as_text: bool = False,
    ) -> None:
        """Show overdue daily tasks sorted by priority."""

        async def tasks_getter() -> Sequence[Task]:
            tasks = await self._get_do_tasks(ctx, category)
            tasks.sort_by_priority()
            return tasks.get_dailies()

        await self._send_tasks(ctx, tasks_getter, as_text=as_text, is_simple=True)

    async def _confirm_task_action(
        self, ctx: dc.Context[Bot], title: str
    ) -> Tuple[Optional[discord.Message], Optional[Task]]:
        profile = await self.get_profile(ctx)
        task = await Task.from_title(self.db, profile, title=title)

        if task is None:
            await BaseCog.send(ctx, f'Task "{title}" not found ❌')
            return None, None

        message = await BaseCog.send(
            ctx,
            "Are you sure?",
            embed=TaskEmbed(self.bot, task),
        )
        is_confirm = await self.wait_for_confirmation(ctx, message)

        if is_confirm:
            return message, task

        return None, None

    @dc.hybrid_command()  # type: ignore[arg-type]
    async def done(self, ctx: dc.Context[Bot], title: str) -> None:
        """Mark a task as done. If the task is not a recurring task, it will get removed."""
        task = await self.task_from_title(ctx, title)

        try:
            await task.done()
        except ValueError as error:
            await BaseCog.send(ctx, str(error))
        else:
            await BaseCog.send(ctx, embed=TaskEmbed(self.bot, task, is_simple=True))

    @dc.hybrid_command()  # type: ignore[arg-type]
    async def cancel(self, ctx: dc.Context[Bot], title: str) -> None:
        """Remove a task."""
        message, task = await self._confirm_task_action(ctx, title)

        if (message is not None) and (task is not None):
            await task.delete()
            await message.edit(
                content="Cancelled ✅",
                embed=TaskEmbed(self.bot, task),
            )

    @dc.hybrid_command()  # type: ignore[arg-type]
    async def showdesc(self, ctx: dc.Context[Bot], title: str) -> None:
        """Show the description of a task."""
        task = await self.task_from_title(ctx, title)
        description = task.description.escaped if task.description else " "
        await BaseCog.send(ctx, f"```\n{description}\n```")


async def setup(bot: Bot) -> None:
    await bot.add_cog(Tasks(bot, bot.db))
