from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from watdo.errors import InvalidData

T = TypeVar("T")
N = TypeVar("N", int, float)


class SafeData(ABC, Generic[T]):
    is_mutable = False

    def __init__(self, value: T) -> None:
        self._value: T
        self._set(value)

    @property
    def value(self) -> T:
        return self._value

    def _set(self, value: T) -> T:
        self.validate(value)
        self._value = value
        return self._value

    def set(self, value: T) -> T:
        if not self.is_mutable:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute 'set'"
            )

        return self._set(value)

    @classmethod
    @abstractmethod
    def validate(cls, value: T) -> None:
        raise NotImplementedError


class String(SafeData[str], ABC):
    min_len: int
    max_len: int

    def _set(self, value: str) -> str:
        return super()._set(value.strip())

    @classmethod
    def validate(cls, value: str) -> None:
        val_len = len(value)

        if val_len > cls.max_len or val_len < cls.min_len:
            raise InvalidData(
                cls,
                f"length should be from {cls.min_len} to {cls.max_len} only.",
            )


class Number(Generic[N], SafeData[N], ABC):
    is_inclusive = True
    min_val: N
    max_val: N

    @classmethod
    def validate(cls, value: N) -> None:
        if cls.is_inclusive:
            if value > cls.max_val or value < cls.min_val:
                raise InvalidData(
                    cls,
                    f"value should be from {cls.min_val} to {cls.max_val} only.",
                )
        else:
            if value >= cls.max_val or value <= cls.min_val:
                raise InvalidData(
                    cls,
                    f"value should be between {cls.min_val} and {cls.max_val} only.",
                )


class Boolean(SafeData[bool]):
    @classmethod
    def validate(cls, value: bool) -> None:
        pass


class UUID(String):
    min_len = 32
    max_len = 32


class SnowflakeID(Number[int]):
    min_val = 10000000000000000
    max_val = 99999999999999999999


class Timestamp(Number[float]):
    min_val = 0
    max_val = 9999999999


class UTCOffset(Number[float]):
    is_inclusive = False
    min_val = -24
    max_val = 24


class RRuleString(String):
    min_len = 7
    max_len = 1000


class TaskTitle(String):
    min_len = 1
    max_len = 200


class TaskCategory(String):
    min_len = 0
    max_len = 50


class TaskDescription(String):
    min_len = 0
    max_len = 4000
