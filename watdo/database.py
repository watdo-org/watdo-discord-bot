import json
from typing import Any, List, Optional, Dict, AsyncIterator, Tuple
from redis.asyncio import Redis
from watdo.models import Task, User
from watdo.environ import REDISHOST, REDISPORT, REDISUSER, REDISPASSWORD


class Database:
    def __init__(self) -> None:
        self._connection: "Redis[Any]" = Redis(
            host=REDISHOST,
            port=REDISPORT,
            username=REDISUSER,
            password=REDISPASSWORD,
        )
        self._cache = DatabaseCache(self)

    async def iter_keys(self, match: str) -> AsyncIterator[str]:
        async for key in self._connection.scan_iter(match=match):
            yield key.decode()

    async def get_user_tasks(
        self,
        uid: str,
        *,
        category: Optional[str] = None,
        ignore_done: bool = False,
    ) -> List[Task]:
        tasks = []
        tasks_data = await self._cache.lrange(f"tasks.{uid}")

        for raw_data in tasks_data:
            task = Task(**json.loads(raw_data))

            if ignore_done and task.is_done:
                continue

            if category is not None:
                if task.category.value != category:
                    continue

            tasks.append(task)

        return tasks

    async def get_user_task(
        self, uid: str, title: str
    ) -> Tuple[Optional[int], Optional[Task]]:
        for index, task in enumerate(await self.get_user_tasks(uid)):
            if task.title.value == title:
                return index, task

        return None, None

    async def add_user_task(self, uid: str, task: Task) -> None:
        await self._cache.lpush(f"tasks.{uid}", task.as_json_str())

    async def set_user_task(self, uid: str, index: int, task: Task) -> None:
        await self._cache.lset(f"tasks.{uid}", index, task.as_json_str())

    async def remove_user_task(self, uid: str, task: Task) -> None:
        await self._cache.lrem(f"tasks.{uid}", task.as_json_str())

    async def get_user_data(self, uid: str) -> Optional[User]:
        data = await self._cache.get(f"user.{uid}")

        if data is None:
            return None

        return User(**json.loads(data))

    async def set_user_data(self, uid: str, data: User) -> None:
        await self._cache.set(f"user.{uid}", data.as_json_str())


class DatabaseCache:
    def __init__(self, database: Database) -> None:
        self.db = database
        self._cache: Dict[str, Any] = {}

    async def get(self, key: str) -> Optional[str]:
        data = self._cache.get(key) or await self.db._connection.get(key)

        if data is None:
            return None

        self._cache[key] = data
        return data

    async def set(self, key: str, value: str) -> None:
        await self.db._connection.set(key, value)
        self._cache[key] = value

    async def lrange(self, key: str) -> List[str]:
        data = self._cache.get(key) or await self.db._connection.lrange(key, 0, -1)
        self._cache[key] = data
        return [d.decode() for d in data]

    async def lpush(self, key: str, value: str) -> None:
        await self.db._connection.lpush(key, value)

        try:
            self._cache[key].insert(0, value)
        except KeyError:
            await self.lrange(key)

    async def lrem(self, key: str, value: str) -> None:
        await self.db._connection.lrem(key, 1, value)
        self._cache[key].remove(value)

    async def lset(self, key: str, index: int, value: str) -> None:
        await self.db._connection.lset(key, index, value)
        self._cache[key][index] = value
