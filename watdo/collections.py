import math
from typing import Generic, TypeVar, Iterator, List
from watdo.models import Task, ScheduledTask

T = TypeVar("T")


class Collection(Generic[T]):
    def __init__(self, items: List[T]) -> None:
        self._items = items

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    @property
    def items(self) -> List[T]:
        return self._items


class TasksCollection(Collection[Task]):
    def sort_by_priority(self) -> "TasksCollection":
        self._items.sort(key=lambda t: t.importance.value, reverse=True)
        self._items.sort(
            key=lambda t: t.due_date.timestamp()
            if isinstance(t, ScheduledTask)
            else math.inf
        )
        self._items.sort(key=lambda t: t.last_done.value if t.last_done else math.inf)
        return self

    def get_dailies(self, *, overdue_only: bool = True) -> List[ScheduledTask[str]]:
        tasks = []

        for task in self._items:
            if not isinstance(task, ScheduledTask):
                continue

            if task.is_daily:
                if overdue_only:
                    if task.is_overdue:
                        tasks.append(task)
                else:
                    tasks.append(task)

        return tasks
