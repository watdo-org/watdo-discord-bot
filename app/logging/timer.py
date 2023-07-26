import time
import logging
from contextlib import contextmanager
from typing import Iterator, Optional, Union
from app.logging import get_logger


@contextmanager
def debug_wall_time(
    logger_name: Union[str, logging.Logger],
    block_name: Optional[str] = None,
) -> Iterator[None]:
    if isinstance(logger_name, logging.Logger):
        logger = logger_name
    else:
        logger = get_logger(logger_name)

    msg = block_name or logger.name
    logger.debug(f"Measuring wall clock time of {msg}...")

    start_time = time.time()
    yield None

    logger.debug(f"Wall clock time of {msg}: {round(time.time() - start_time, 2)}s")


@contextmanager
def debug_cpu_time(
    logger_name: Union[str, logging.Logger],
    block_name: Optional[str] = None,
) -> Iterator[None]:
    if isinstance(logger_name, logging.Logger):
        logger = logger_name
    else:
        logger = get_logger(logger_name)

    msg = block_name or logger.name
    logger.debug(f"Measuring CPU time of {msg}...")

    start_time = time.process_time()
    yield None

    logger.debug(f"CPU time of {msg}: {round(time.process_time() - start_time, 2)}s")
