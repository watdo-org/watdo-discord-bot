import json
from typing import Any, List, Optional, Dict, AsyncIterator
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

    async def get_user_task(self, uid: str, title: str) -> Optional[Task]:
        for task in await self.get_user_tasks(uid):
            if task.title.value == title:
                return task

        return None

    async def add_user_task(self, uid: str, task: Task) -> None:
        await self._cache.lpush(f"tasks.{uid}", task.as_json_str())

    async def set_user_task(self, uid: str, old_task_str: str, new_task: Task) -> None:
        for index, task in enumerate(await self.get_user_tasks(uid)):
            if task.as_json_str() == old_task_str:
                await self._cache.lset(f"tasks.{uid}", index, new_task.as_json_str())
                break

    async def remove_user_task(self, uid: str, task: Task) -> None:
        await self._cache.lrem(f"tasks.{uid}", task.as_json_str())

    async def get_user_data(self, uid: str) -> Optional[User]:
        data = await self._cache.get(f"user.{uid}")

        if data is None:
            return None

        return User(**json.loads(data))

    async def set_user_data(self, uid: str, data: User) -> None:
        await self._cache.set(f"user.{uid}", data.as_json_str())

    async def get_command_shortcut(self, uid: str, name: str) -> Optional[str]:
        return await self._cache.hget(f"shortcuts.{uid}", name)

    async def get_all_command_shortcuts(self, uid: str) -> Dict[str, str]:
        return await self._cache.hgetall(f"shortcuts.{uid}")

    async def set_command_shortcut(self, uid: str, name: str, command: str) -> None:
        await self._cache.hset(f"shortcuts.{uid}", key=name, value=command)

    async def delete_command_shortcut(self, uid: str, name: str) -> int:
        return await self._cache.hdel(f"shortcuts.{uid}", name)


class DatabaseCache:
    def __init__(self, database: Database) -> None:
        self.db = database
        self._str_cache: Dict[str, str] = {}
        self._list_cache: Dict[str, List[str]] = {}
        self._hash_cache: Dict[str, Dict[str, str]] = {}

    async def get(self, key: str) -> Optional[str]:
        data = self._str_cache.get(key) or await self.db._connection.get(key)

        if data is None:
            return None

        data = data.decode() if isinstance(data, bytes) else data
        self._str_cache[key] = data
        return data

    async def set(self, key: str, value: str) -> None:
        await self.db._connection.set(key, value)
        self._str_cache[key] = value

    async def lrange(self, key: str) -> List[str]:
        data = self._list_cache.get(key) or await self.db._connection.lrange(key, 0, -1)
        data = [d.decode() if isinstance(d, bytes) else d for d in data]
        self._list_cache[key] = data
        return data

    async def lpush(self, key: str, value: str) -> None:
        await self.db._connection.lpush(key, value)

        try:
            self._list_cache[key].insert(0, value)
        except KeyError:
            await self.lrange(key)

    async def lrem(self, key: str, value: str) -> None:
        await self.db._connection.lrem(key, 1, value)
        self._list_cache[key].remove(value)

    async def lset(self, key: str, index: int, value: str) -> None:
        await self.db._connection.lset(key, index, value)
        self._list_cache[key][index] = value

    async def hgetall(self, name: str) -> Dict[str, str]:
        data = await self.db._connection.hgetall(name)
        data = {k.decode(): v.decode() for k, v in data.items()}
        self._hash_cache[name] = data
        return data

    async def hget(self, name: str, key: str) -> Optional[str]:
        cache = self._hash_cache.get(name)

        if cache is None:
            data = await self.db._connection.hget(name, key)
        else:
            data = cache.get(key) or await self.db._connection.hget(name, key)

        if data is None:
            return None

        data = data.decode() if isinstance(data, bytes) else data

        try:
            self._hash_cache[name][key] = data
        except KeyError:
            self._hash_cache[name] = {key: data}

        return data

    async def hset(self, name: str, *, key: str, value: str) -> None:
        await self.db._connection.hset(name, key=key, value=value)

        try:
            self._hash_cache[name]
        except KeyError:
            await self.hget(name, key)

        self._hash_cache[name][key] = value

    async def hdel(self, name: str, *keys: str) -> int:
        deleted_count = await self.db._connection.hdel(name, *keys)

        for key in keys:
            try:
                del self._hash_cache[name][key]
            except KeyError:
                pass

        return deleted_count
