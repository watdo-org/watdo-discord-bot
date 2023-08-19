import json
from uuid import uuid4
from abc import ABC, abstractmethod
from typing import cast, Optional, Dict, Any, TypeVar, Generic, List
from dateutil import rrule
import recurrent
from watdo import dt
from watdo.database import Database
from watdo.safe_data import (
    SafeData,
    Boolean,
    UUID,
    Timestamp,
    UTCOffset,
    SnowflakeID,
    RRuleString,
    TaskTitle,
    TaskCategory,
    TaskDescription,
)

DueT = TypeVar("DueT", str, float)


class Model(ABC):
    """A unique data entity of a given database."""

    def __init__(
        self,
        database: Database,
        *,
        uuid: str,
        created_at: float,
        created_by: int,
    ) -> None:
        self._database = database
        self.uuid = UUID(uuid)
        self.created_at = Timestamp(created_at)
        self.created_by = SnowflakeID(created_by)

        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue

            if value is None:
                continue

            if not isinstance(value, SafeData):
                t = type(value).__name__
                raise TypeError(f"\"{key}\": '{t}' should be 'SafeData'")

    @property
    def db(self) -> Database:
        return self._database

    def as_json(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {}

        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue

            if value is None:
                res[key] = value
            else:
                res[key] = value.value

        return res

    def as_json_str(self, *, indent: Optional[int] = None) -> str:
        return json.dumps(self.as_json(), indent=indent)

    @abstractmethod
    async def save(self) -> None:
        raise NotImplementedError


class Profile(Model):
    @classmethod
    async def from_channel_id(
        cls, db: Database, channel_id: int
    ) -> Optional["Profile"]:
        profile_id = await db.get(f"profile:channel.{channel_id}")

        if profile_id is None:
            return None

        return await cls.from_id(db, profile_id)

    @classmethod
    async def from_id(cls, db: Database, uuid: str) -> Optional["Profile"]:
        raw_data = await db.get(f"profile.{uuid}")

        if raw_data is None:
            return None

        return cls(db, **json.loads(raw_data))

    def __init__(
        self,
        database: Database,
        *,
        utc_offset: float,
        uuid: str,
        created_at: float,
        created_by: int,
    ) -> None:
        self.utc_offset = UTCOffset(utc_offset)
        super().__init__(
            database, uuid=uuid, created_at=created_at, created_by=created_by
        )

    async def save(self) -> None:
        await self.db.set(f"profile.{self.uuid.value}", self.as_json_str())

    async def add_channel(self, channel_id: int) -> None:
        await self.db.set(f"profile:channel.{channel_id}", self.uuid.value)


class Task(Model):
    @staticmethod
    def _fix_data(profile: Profile, data: Dict[str, Any]) -> None:
        should_update = False
        keys_to_delete = ("channel_id", "utc_offset_hour")
        keys_to_delete_if_not_scheduled = (
            "due",
            "has_reminder",
            "is_auto_done",
            "next_reminder",
        )

        for key in keys_to_delete:
            try:
                del data[key]
                should_update = True
            except KeyError:
                pass

        if data.get("due") is None:
            for key in keys_to_delete_if_not_scheduled:
                try:
                    del data[key]
                    should_update = True
                except KeyError:
                    pass

        if data.get("profile_id") is None:
            data["profile_id"] = profile.uuid.value
            should_update = True

        if data.get("uuid") is None:
            data["uuid"] = uuid4().hex
            should_update = True

        if data.get("created_by") is None:
            data["created_by"] = profile.created_by.value
            should_update = True

    @staticmethod
    async def get_tasks_of_profile(
        db: Database,
        profile: Profile,
        *,
        category: Optional[str] = None,
        ignore_done: bool = False,
    ) -> List["Task"]:
        tasks_data = await db.lrange(f"tasks:profile.{profile.uuid.value}")
        tasks = []

        for raw_data in tasks_data:
            data = json.loads(raw_data)
            Task._fix_data(profile, data)

            if data.get("due") is None:
                task = Task(db, profile=profile, **data)
            else:
                task = ScheduledTask(db, profile=profile, **data)

            if ignore_done and task.is_done:
                continue

            if category is not None:
                if task.category.value != category:
                    continue

            tasks.append(task)

        return tasks

    def __init__(
        self,
        database: Database,
        *,
        profile: Profile,
        title: str,
        category: str,
        is_important: bool,
        description: Optional[str] = None,
        last_done: Optional[float] = None,
        profile_id: str,
        uuid: str,
        created_at: float,
        created_by: int,
    ) -> None:
        self._profile = profile
        self._timezone = dt.utc_offset_to_tz(self._profile.utc_offset.value)

        self.title = TaskTitle(title)
        self.category = TaskCategory(category)
        self.is_important = Boolean(is_important)
        self.description = TaskDescription(description) if description else None
        self.last_done = Timestamp(last_done) if last_done else None
        self.profile_id = UUID(profile_id)

        super().__init__(
            database, uuid=uuid, created_at=created_at, created_by=created_by
        )

    @property
    def tz(self) -> dt.timezone:
        return self._timezone

    @property
    def date_created(self) -> dt.datetime:
        return dt.fromtimestamp(self.created_at.value, self._profile.utc_offset.value)

    @property
    def is_done(self) -> bool:
        return self.last_done is not None

    @property
    def last_done_date(self) -> Optional[dt.datetime]:
        if self.last_done is None:
            return None

        return dt.fromtimestamp(self.last_done.value, self._profile.utc_offset.value)

    async def save(self) -> None:
        await self.db.lpush(
            f"tasks:profile.{self._profile.uuid.value}", self.as_json_str()
        )


class ScheduledTask(Task, Generic[DueT]):
    def __init__(
        self,
        database: Database,
        *,
        profile: Profile,
        title: str,
        category: str,
        is_important: bool,
        description: Optional[str] = None,
        last_done: Optional[float] = None,
        profile_id: str,
        due: DueT,
        has_reminder: bool = True,
        is_auto_done: bool = False,
        next_reminder: Optional[float] = None,
        uuid: str,
        created_at: float,
        created_by: int,
    ) -> None:
        self.due: RRuleString | Timestamp
        self.has_reminder = Boolean(has_reminder)
        self.is_auto_done = Boolean(is_auto_done)
        self.next_reminder = Timestamp(next_reminder) if next_reminder else None

        if isinstance(due, float):
            self.due = Timestamp(due)
        elif isinstance(due, str):
            self.due = RRuleString(due)

            # Set timezone to rrule
            tz = dt.utc_offset_to_tz(profile.utc_offset.value)
            dtstart = rrule.rrulestr(due)._dtstart.replace(tzinfo=tz)  # type: ignore[union-attr]
            self._rrule: rrule.rrule = cast(
                rrule.rrule, rrule.rrulestr(due.split("\n")[1], dtstart=dtstart)
            )

        super().__init__(
            database,
            profile=profile,
            title=title,
            category=category,
            is_important=is_important,
            description=description,
            last_done=last_done,
            profile_id=profile_id,
            uuid=uuid,
            created_at=created_at,
            created_by=created_by,
        )

    @property
    def is_recurring(self) -> bool:
        return isinstance(self.due.value, str)

    @property
    def is_done(self) -> bool:
        if not self.is_recurring:
            return self.last_done is not None

        if self.last_done is None:
            return False

        if self.next_reminder is None:
            return self.last_done is not None

        return self.due_date.timestamp() == self.next_reminder.value

    @property
    def rrule(self) -> rrule.rrule:
        if isinstance(self._rrule, rrule.rrule):
            return self._rrule

        raise TypeError(self._rrule)

    @property
    def rrulestr(self) -> str:
        return recurrent.format(
            str(self._rrule),
            now=dt.date_now(self._profile.utc_offset.value),
        )

    @property
    def due_date(self) -> dt.datetime:
        due = self.due.value

        if isinstance(due, float):
            return dt.fromtimestamp(due, self._profile.utc_offset.value)

        return self._rrule.after(self.last_done_date or self._rrule._dtstart)  # type: ignore[attr-defined]

    @property
    def is_overdue(self) -> bool:
        if self.due_date < dt.date_now(self._profile.utc_offset.value):
            return True

        return False
