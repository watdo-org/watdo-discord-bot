import asyncio
from typing import cast, List
import pytest
from watdo.database import Database
from watdo.logging import debug_wall_time


@pytest.fixture
def loop() -> asyncio.AbstractEventLoop:
    return asyncio.new_event_loop()


class TestDatabase:
    def test_get(self, loop: asyncio.AbstractEventLoop) -> None:
        db = Database()
        deltas: List[float] = []

        for _ in range(2):
            with debug_wall_time("") as result:
                loop.run_until_complete(db.get("test"))

            deltas.append(cast(float, result["delta"]))

        assert deltas[0] / 4 > deltas[1]
