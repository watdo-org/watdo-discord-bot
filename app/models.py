import math
import json
from abc import ABC
import datetime as dt
from typing import Dict, Any, Optional
from app.safe_data import SafeData, String, Boolean, Number


class Model(ABC):
    def __init__(self) -> None:
        for key, value in self.__dict__.items():
            if value is None:
                continue

            if not isinstance(value, SafeData):
                t = type(value).__name__
                raise TypeError(f"\"{key}\": '{t}' should be 'SafeData[{t}]'")

    def as_json(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {}

        for key, value in self.__dict__.items():
            if value is None:
                res[key] = value
            else:
                res[key] = value.value

        return res

    def as_json_str(self, *, indent: Optional[int] = None) -> str:
        return json.dumps(self.as_json(), indent=indent)


class Task(Model):
    def __init__(
        self,
        *,
        title: str,
        category: str,
        is_important: bool,
        due_seconds: Optional[float],
    ) -> None:
        self.title = String(title, min_len=1, max_len=1000)
        self.category = String(category, min_len=0, max_len=100)
        self.is_important = Boolean(is_important)
        self.due_seconds = (
            Number(due_seconds, min_val=1, max_val=math.inf)
            if due_seconds is not None
            else None
        )
        super().__init__()

    @property
    def due_date(self) -> Optional[dt.datetime]:
        if self.due_seconds is None:
            return None

        return dt.datetime.fromtimestamp(self.due_seconds.value)
