import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from watdo.database import Database
from watdo.safe_data import SafeData, UUID, Timestamp, UTCOffset, SnowflakeID


class Model(ABC):
    """A unique data entity."""

    def __init__(
        self,
        *,
        uuid: str,
        created_at: float,
        created_by: int,
    ) -> None:
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
    async def save(self, db: Database) -> None:
        raise NotImplementedError


class Profile(Model):
    @classmethod
    async def from_channel_id(
        cls, db: Database, channel_id: int
    ) -> Optional["Profile"]:
        profile_id = await db.get(f"profile:channel.{channel_id}")
        raw_data = await db.get(f"profile.{profile_id}")

        if raw_data is None:
            return None

        return cls(**json.loads(raw_data))

    def __init__(
        self,
        *,
        utc_offset: float,
        uuid: str,
        created_at: float,
        created_by: int,
    ) -> None:
        self.utc_offset = UTCOffset(utc_offset)
        super().__init__(uuid=uuid, created_at=created_at, created_by=created_by)

    async def save(self, db: Database) -> None:
        await db.set(f"profile.{self.uuid.value}", self.as_json_str())

    async def add_to_channel(self, db: Database, channel_id: int) -> None:
        await db.set(f"profile:channel.{channel_id}", self.uuid.value)
