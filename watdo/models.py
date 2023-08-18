from abc import ABC
from watdo.safe_data import SafeData, UUID, Timestamp, UTCOffset


class Model(ABC):
    """A unique data entity."""

    def __init__(self, *, uuid: UUID, created_at: Timestamp) -> None:
        self.uuid = uuid
        self.created_at = created_at

        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue

            if value is None:
                continue

            if not isinstance(value, SafeData):
                t = type(value).__name__
                raise TypeError(f"\"{key}\": '{t}' should be 'SafeData'")


class Profile(Model):
    def __init__(
        self,
        *,
        creator_id: UUID,
        utc_offset: UTCOffset,
        uuid: UUID,
        created_at: Timestamp,
    ) -> None:
        self.creator_id = creator_id
        self.utc_offset = utc_offset
        super().__init__(uuid=uuid, created_at=created_at)
