from typing import TYPE_CHECKING, Any, Type
from discord.ext import commands as dc

if TYPE_CHECKING:
    from watdo.safe_data import SafeData


class CancelCommand(dc.CommandError):
    pass


class CustomException(Exception):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)


class InvalidData(CustomException):
    def __init__(self, cls: "Type[SafeData[Any]]", message: str, *args: object) -> None:
        super().__init__(f"{cls.__name__} {message}", *args)
