import math
import json
from abc import ABC
import datetime as dt
from typing import cast, Dict, Any, Optional
from dateutil import rrule
from app.safe_data import SafeData, String, Boolean, Timestamp


class Model(ABC):
    def __init__(self, *, created_at: float) -> None:
        self.created_at = Timestamp(created_at)

        for key, value in self.__dict__.items():
            if key.startswith("_"):
                continue

            if value is None:
                continue

            if not isinstance(value, SafeData):
                t = type(value).__name__
                raise TypeError(f"\"{key}\": '{t}' should be 'SafeData[{t}]'")

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

    @property
    def date_created(self) -> dt.datetime:
        return dt.datetime.fromtimestamp(self.created_at.value)


class Task(Model):
    def __init__(
        self,
        *,
        title: str,
        category: str,
        is_important: bool,
        due: Optional[float | str],
        last_done: Optional[float] = None,
        next_reminder: Optional[float] = None,
        created_at: float,
    ) -> None:
        self.title = String(title, min_len=1, max_len=1000)
        self.category = String(category, min_len=0, max_len=100)
        self.is_important = Boolean(is_important)
        self.due: Optional[Timestamp | String]
        self.last_done = Timestamp(last_done) if last_done else None
        self.next_reminder = Timestamp(next_reminder) if next_reminder else None

        if due is None:
            self.due = None
        elif isinstance(due, float):
            self.due = Timestamp(due)
        elif isinstance(due, str):
            self.due = String(due, min_len=7, max_len=math.inf)
            self._rrule = rrule.rrulestr(due)

        super().__init__(created_at=created_at)

    @property
    def rrule(self) -> rrule.rrule:
        if isinstance(self._rrule, rrule.rrule):
            return self._rrule

        raise TypeError(self._rrule)

    @property
    def due_date(self) -> Optional[dt.datetime]:
        if self.due is None:
            return None

        due = self.due.value

        if isinstance(due, float):
            return dt.datetime.fromtimestamp(due)

        return self._rrule.after(self.last_done_date or self.date_created)

    @property
    def last_done_date(self) -> Optional[dt.datetime]:
        if self.last_done is None:
            return None

        return dt.datetime.fromtimestamp(self.last_done.value)

    @property
    def is_recurring(self) -> bool:
        if self.due is None:
            return False

        return isinstance(self.due.value, str)

    @property
    def is_done(self) -> bool:
        if not self.is_recurring:
            return self.last_done is not None

        if self.last_done is None:
            return False

        if self.next_reminder is None:
            return self.last_done is not None

        return cast(dt.datetime, self.due_date).timestamp() == self.next_reminder.value
