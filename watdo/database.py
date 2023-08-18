from typing import Dict, List, Optional
from redis.asyncio import Redis
from watdo.environ import REDIS_URL


class Database:
    _conn = Redis.from_url(REDIS_URL)

    def __init__(self) -> None:
        self._str_cache: Dict[str, str] = {}
        self._list_cache: Dict[str, List[str]] = {}
        self._hash_cache: Dict[str, Dict[str, str]] = {}

    async def get(self, key: str) -> Optional[str]:
        data = self._str_cache.get(key) or await self._conn.get(key)

        if data is None:
            return None

        data = data.decode() if isinstance(data, bytes) else data
        self._str_cache[key] = data
        return data

    async def set(self, key: str, value: str) -> None:
        await self._conn.set(key, value)
        self._str_cache[key] = value

    async def lrange(self, key: str) -> List[str]:
        data = self._list_cache.get(key) or await self._conn.lrange(key, 0, -1)
        data = [d.decode() if isinstance(d, bytes) else d for d in data]
        self._list_cache[key] = data
        return data

    async def lpush(self, key: str, value: str) -> None:
        await self._conn.lpush(key, value)

        try:
            self._list_cache[key].insert(0, value)
        except KeyError:
            await self.lrange(key)

    async def lrem(self, key: str, value: str) -> None:
        await self._conn.lrem(key, 1, value)

        try:
            self._list_cache[key].remove(value)
        except ValueError:
            await self.lrange(key)

    async def lset(self, key: str, index: int, value: str) -> None:
        await self._conn.lset(key, index, value)
        self._list_cache[key][index] = value

    async def hgetall(self, name: str) -> Dict[str, str]:
        data = await self._conn.hgetall(name)
        data = {k.decode(): v.decode() for k, v in data.items()}
        self._hash_cache[name] = data
        return data

    async def hget(self, name: str, key: str) -> Optional[str]:
        cache = self._hash_cache.get(name)

        if cache is None:
            data = await self._conn.hget(name, key)
        else:
            data = cache.get(key) or await self._conn.hget(name, key)

        if data is None:
            return None

        data = data.decode() if isinstance(data, bytes) else data

        try:
            self._hash_cache[name][key] = data
        except KeyError:
            self._hash_cache[name] = {key: data}

        return data

    async def hset(self, name: str, *, key: str, value: str) -> None:
        await self._conn.hset(name, key=key, value=value)

        try:
            self._hash_cache[name]
        except KeyError:
            await self.hget(name, key)

        self._hash_cache[name][key] = value

    async def hdel(self, name: str, *keys: str) -> int:
        deleted_count = await self._conn.hdel(name, *keys)

        for key in keys:
            try:
                del self._hash_cache[name][key]
            except KeyError:
                pass

        return deleted_count
