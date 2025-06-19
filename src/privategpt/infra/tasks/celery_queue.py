from __future__ import annotations

"""Celery-backed implementation of the TaskQueuePort abstraction."""

from celery import Celery

from privategpt.core.ports.task_queue import TaskQueuePort
from privategpt.infra.tasks.celery_app import app as celery_app
from privategpt.shared.logging import get_logger

logger = get_logger("task_queue.celery")


class CeleryTaskQueueAdapter(TaskQueuePort):
    """Adapter that forwards `enqueue` calls to a running Celery application."""

    def __init__(self, app: Celery | None = None):
        # allow injection of a custom Celery instance for tests
        self._app: Celery = app or celery_app

    # noqa: D401 – simple protocol implementation
    def enqueue(self, task_name: str, *args, **kwargs) -> str:  # type: ignore[override]
        result = self._app.send_task(task_name, args=args, kwargs=kwargs)
        logger.info("task.enqueue", task=task_name, task_id=result.id)
        return result.id 