import json
from abc import ABC, abstractmethod
from typing import cast, Optional, Dict, Any, TypeVar, Generic
from dateutil import rrule
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
        self.db = database
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

        return cls(**json.loads(raw_data))

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
        profile_id: int,
        uuid: str,
        created_at: float,
        created_by: int,
    ) -> None:
        self._profile = profile
        self.tz = dt.utc_offset_to_tz(self._profile.utc_offset.value)

        self.title = TaskTitle(title)
        self.category = TaskCategory(category)
        self.is_important = Boolean(is_important)
        self.description = TaskDescription(description) if description else None
        self.last_done = Timestamp(last_done) if last_done else None
        self.profile_id = SnowflakeID(profile_id)

        super().__init__(
            database, uuid=uuid, created_at=created_at, created_by=created_by
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
        profile_id: int,
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
    def rrule(self) -> rrule.rrule:
        if isinstance(self._rrule, rrule.rrule):
            return self._rrule

        raise TypeError(self._rrule)
