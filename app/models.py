import math
from abc import ABC
from typing import Dict, Any
from app.safe_data import SafeData, String, Boolean, Number


class Model(ABC):
    def __init__(self) -> None:
        for key, value in self.__dict__.items():
            if not isinstance(value, SafeData):
                t = type(value).__name__
                raise TypeError(f"\"{key}\": '{t}' should be 'SafeData[{t}]'")

    def as_json(self) -> Dict[str, SafeData[Any]]:
        return self.__dict__


class Task(Model):
    def __init__(
        self,
        *,
        title: str,
        category: str,
        is_important: bool,
        due_seconds: float,
    ) -> None:
        self.title = String(title, min_len=1, max_len=1000)
        self.category = String(category, min_len=0, max_len=100)
        self.is_important = Boolean(is_important)
        self.due_seconds = Number(due_seconds, min_val=1, max_val=math.inf)
        super().__init__()
