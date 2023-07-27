import json
from typing import Any, List, Optional
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

    async def get_user_tasks(
        self, uid: str, *, category: Optional[str] = None
    ) -> List[Task]:
        tasks = []
        tasks_data = await self._conn.lrange(uid, 0, -1)

        for raw_data in tasks_data:
            task = Task(**json.loads(raw_data))

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
        await self._conn.lpush(uid, task.as_json_str())

    async def remove_user_task(self, uid: str, task: Task) -> None:
        await self._conn.lrem(uid, 1, task.as_json_str())
