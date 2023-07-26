import json
from typing import Any, List
from redis.asyncio import Redis
from app.models import Task
from app.environ import REDISHOST, REDISPORT, REDISUSER, REDISPASSWORD


class Database:
    def __init__(self) -> None:
        self._conn: "Redis[Any]" = Redis(
            host=REDISHOST,
            port=REDISPORT,
            username=REDISUSER,
            password=REDISPASSWORD,
        )

    async def get_user_tasks(self, uid: str) -> List[Task]:
        tasks = []
        tasks_data = await self._conn.lrange(uid, 0, -1)

        for raw_data in tasks_data:
            data = json.loads(raw_data)
            tasks.append(Task(**data))

        return tasks
