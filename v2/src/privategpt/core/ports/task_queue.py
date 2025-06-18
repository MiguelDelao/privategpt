from __future__ import annotations

from typing import Protocol, Any


class TaskQueuePort(Protocol):
    def enqueue(self, task_name: str, *args: Any, **kwargs: Any) -> str: ... 