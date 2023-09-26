from typing import Dict, List, Optional, AsyncIterator
from redis.asyncio import Redis
from watdo.environ import REDIS_URL


class Database:
    _conn = Redis.from_url(REDIS_URL)

    async def iter_keys(self, match: str) -> AsyncIterator[str]:
        async for key in self._conn.scan_iter(match=match):
            yield key.decode()

    async def get(self, key: str) -> Optional[str]:
        data = await self._conn.get(key)

        if data is None:
            return None

        data = data.decode() if isinstance(data, bytes) else data
        return data

    async def set(self, key: str, value: str) -> None:
        await self._conn.set(key, value)

    async def lrange(self, key: str) -> List[str]:
        data = await self._conn.lrange(key, 0, -1)
        data = [d.decode() if isinstance(d, bytes) else d for d in data]
        return data

    async def lpush(self, key: str, value: str) -> None:
        await self._conn.lpush(key, value)

    async def lrem(self, key: str, value: str) -> None:
        await self._conn.lrem(key, 1, value)

    async def lset(self, key: str, index: int, value: str) -> None:
        await self._conn.lset(key, index, value)

    async def hgetall(self, name: str) -> Dict[str, str]:
        data = await self._conn.hgetall(name)
        data = {k.decode(): v.decode() for k, v in data.items()}
        return data

    async def hget(self, name: str, key: str) -> Optional[str]:
        data = await self._conn.hget(name, key)

        if data is None:
            return None

        data = data.decode() if isinstance(data, bytes) else data
        return data

    async def hset(self, name: str, *, key: str, value: str) -> None:
        await self._conn.hset(name, key=key, value=value)

    async def hdel(self, name: str, *keys: str) -> int:
        deleted_count = await self._conn.hdel(name, *keys)
        return deleted_count

    def _parse_shortcuts(self, command_str: Optional[str]) -> Optional[List[str]]:
        if command_str is None:
            return None

        if len(command_str) == 0:
            return None

        return command_str.split("==%SEPARATOR%==")

    async def get_command_shortcut(
        self, user_id: str, name: str
    ) -> Optional[List[str]]:
        res = await self.hget(f"shortcuts:user.{user_id}", name)
        return self._parse_shortcuts(res)

    async def get_all_command_shortcuts(self, user_id: str) -> Dict[str, List[str]]:
        res = await self.hgetall(f"shortcuts:user.{user_id}")
        shortcuts = {}

        for name, command in res.items():
            shortcuts[name] = self._parse_shortcuts(command) or [" "]

        return shortcuts

    async def set_command_shortcut(
        self, user_id: str, name: str, command: List[str]
    ) -> None:
        await self.hset(
            f"shortcuts:user.{user_id}",
            key=name,
            value="==%SEPARATOR%==".join(command),
        )

    async def delete_command_shortcut(self, user_id: str, name: str) -> int:
        return await self.hdel(f"shortcuts:user.{user_id}", name)
