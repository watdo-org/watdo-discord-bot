from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from watdo.errors import InvalidData

T = TypeVar("T")
N = TypeVar("N", int, float)


class SafeData(ABC, Generic[T]):
    is_mutable = False

    def __init__(self, value: T) -> None:
        self._value: T
        self.set(value)

    @property
    def value(self) -> T:
        return self._value

    def set(self, value: T) -> T:
        if not self.is_mutable:
            raise AttributeError(
                f"'{self.__class__.__name__}' object has no attribute 'set'"
            )

        self.validate(value)
        self._value = value
        return self._value

    @classmethod
    @abstractmethod
    def validate(cls, value: T) -> None:
        raise NotImplementedError


class String(SafeData[str], ABC):
    min_len: int
    max_len: int

    @classmethod
    def validate(cls, value: str) -> None:
        val_len = len(value)

        if val_len > cls.max_len or val_len < cls.min_len:
            raise InvalidData(
                cls,
                f"length should be from {cls.min_len} to {cls.max_len} only",
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
                    f"value should be from {cls.min_val} to {cls.max_val} only",
                )
        else:
            if value >= cls.max_val or value <= cls.min_val:
                raise InvalidData(
                    cls,
                    f"value should be between {cls.min_val} and {cls.max_val} only",
                )


class UUID(String):
    pass


class Timestamp(Number[float]):
    pass


class UTCOffset(Number[float]):
    is_inclusive = False
