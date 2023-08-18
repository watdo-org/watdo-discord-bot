import asyncio
from watdo.logging import get_logger
from watdo._main_runner import async_main_runner


async def async_main(loop: asyncio.AbstractEventLoop) -> int:
    get_logger("main").info("Hello world!!")
    return 0


def main() -> int:
    return async_main_runner(async_main)
