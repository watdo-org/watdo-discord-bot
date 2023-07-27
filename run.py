import os
import sys
import asyncio
import threading
from types import TracebackType
from typing import Any, Callable, Coroutine, Dict, Type, Optional
from app.logging import get_logger

_LOGGERS = {
    name: get_logger(name)
    for name in (
        "excepthook",
        "asyncio_exception_handler",
    )
}


def excepthook(
    exc_type: Type[BaseException],
    exc_value: Optional[BaseException],
    exc_traceback: Optional[TracebackType],
) -> None:
    try:
        _LOGGERS["excepthook"].critical(
            repr(exc_value), exc_info=exc_value, stack_info=True
        )
    except Exception:
        sys.__excepthook__(exc_type, exc_value or exc_type(None), exc_traceback)


def asyncio_exception_handler(
    loop: asyncio.AbstractEventLoop,
    context: Dict[str, Any],
) -> None:
    exception = context.get("exception")

    if exception is None:
        _LOGGERS["asyncio_exception_handler"].warning(context)
    else:
        excepthook(type(exception), exception, None)


def set_error_handlers(*, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    sys.excepthook = excepthook
    threading.excepthook = lambda args: excepthook(
        args.exc_type,
        args.exc_value,
        args.exc_traceback,
    )

    if loop is not None:
        loop.set_exception_handler(asyncio_exception_handler)


def async_runner(
    entry_point_function: Callable[
        [asyncio.AbstractEventLoop], Coroutine[Any, Any, None]
    ]
) -> None:
    if os.name == "nt":
        loop_factory = None
    else:
        import uvloop

        loop_factory = uvloop.new_event_loop

    try:
        with asyncio.Runner(loop_factory=loop_factory) as runner:
            loop = runner.get_loop()
            set_error_handlers(loop=loop)
            runner.run(entry_point_function(loop))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    from app import main

    async_runner(main)
