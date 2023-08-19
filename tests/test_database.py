import asyncio
from typing import cast, List, Any
from watdo.database import Database
from watdo.logging import debug_wall_time

loop = asyncio.new_event_loop()


class TestDatabase:
    def ensure_second_db_call_is_faster(
        self, method: str, *args: Any, **kwargs: Any
    ) -> None:
        db = Database()
        deltas: List[float] = []

        for _ in range(2):
            func = getattr(db, method)
            coro = func(*args, **kwargs)

            with debug_wall_time("") as result:
                loop.run_until_complete(coro)

            deltas.append(cast(float, result["delta"]))

        assert deltas[0] > deltas[1]

    def test_get(self) -> None:
        self.ensure_second_db_call_is_faster(
            "get",
            "profile.6e0a3e69c27f45a1ae7596debcd01587",
        )

    def test_lrange(self) -> None:
        self.ensure_second_db_call_is_faster(
            "lrange",
            "tasks:profile.6e0a3e69c27f45a1ae7596debcd01587",
        )
