"""Tasks: list, show and wait for them (docs/cli.md §6, §10)."""

from __future__ import annotations

import sqlite3
import time
from contextlib import closing
from datetime import datetime
from typing import Any

from wordcut.db import connect, tasks
from wordcut.db.tasks import TaskRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.lock import LockHolder, ProcessingLock
from wordcut.tasks import Progress, ProgressListener, Result
from wordcut.tasks.processes import is_running, this_host

# docs/cli.md §6.1; the CHECK of migration 0003 lists the same states.
TASK_STATES = ("running", "succeeded", "failed")
# docs/cli.md §6.1: the kinds commands launch. The internal diagnostic kind is not one of them.
TASK_KINDS = ("process", "render", "suggest")

ORPHAN_MESSAGE = "A tarefa foi interrompida: o processo dela terminou antes do fim."

# A wait reads the task this often; it works across processes and containers.
WAIT_POLL_SECONDS = 0.5


def launched_task(task: TaskRow) -> dict[str, Any]:
    """The answer to a launch that does not wait (docs/cli.md §6.2)."""
    return {
        "task_id": task.id,
        "kind": task.kind,
        "status": task.status,
        f"{task.resource_type}_id": task.resource_id,
    }


def list_tasks(home: Home, status: str | None = None, kind: str | None = None) -> dict[str, Any]:
    """Tasks with the latest start first, only those in ``status`` and of ``kind`` when given."""
    with closing(connect(home)) as connection:
        _reconcile(home, connection, tasks.newest_first(connection, "running"))
        found = tasks.newest_first(connection, status, kind)
    return {"items": [_shown(task) for task in found]}


def show_task(home: Home, task_id: int) -> dict[str, Any]:
    """Kind, status, resource, start, end, progress, error and result of the task."""
    with closing(connect(home)) as connection:
        return _shown(_existing(home, connection, task_id))


def wait_task(
    home: Home,
    task_id: int,
    on_progress: ProgressListener | None = None,
    poll_seconds: float = WAIT_POLL_SECONDS,
) -> Result:
    """Wait for the task to end and give its result, or raise the error it failed with.

    ``on_progress`` hears each new progress of the running task. Waiting never changes the
    task: interrupting the wait leaves it running.
    """
    heard: tuple[float, str] | None = None
    while True:
        with closing(connect(home)) as connection:
            task = _existing(home, connection, task_id)
        if task.status == "succeeded":
            return task.result or {}
        if task.status == "failed":
            raise _failure(task)
        if on_progress is not None and task.progress_message is not None:
            progress = (task.progress, task.progress_message)
            if progress != heard:
                on_progress(Progress(task.id, task.kind, *progress))
                heard = progress
        time.sleep(poll_seconds)


def _existing(home: Home, connection: sqlite3.Connection, task_id: int) -> TaskRow:
    task = _found(connection, task_id)
    if _reconcile(home, connection, [task]):
        task = _found(connection, task_id)
    return task


def _found(connection: sqlite3.Connection, task_id: int) -> TaskRow:
    task = tasks.by_id(connection, task_id)
    if task is None:
        raise WordcutError("not_found", f"Tarefa {task_id} não existe.", {"task_id": task_id})
    return task


def _reconcile(home: Home, connection: sqlite3.Connection, found: list[TaskRow]) -> bool:
    """Mark ``failed`` the running tasks whose process is gone; true if there was one."""
    holder = ProcessingLock(home).holder()
    orphans = [task for task in found if task.status == "running" and _is_orphan(task, holder)]
    for task in orphans:
        tasks.finish_failed(connection, task.id, "interrupted", ORPHAN_MESSAGE, None, _now())
    return bool(orphans)


def _is_orphan(task: TaskRow, holder: LockHolder | None) -> bool:
    if holder is not None and holder.task_id == task.id:
        return False
    # Another host is another PID namespace (another container): its PID says nothing here.
    return task.host == this_host() and not is_running(task.pid)


def _shown(task: TaskRow) -> dict[str, Any]:
    return {
        "id": task.id,
        "kind": task.kind,
        "status": task.status,
        f"{task.resource_type}_id": task.resource_id,
        "progress": task.progress,
        "progress_message": task.progress_message,
        "pid": task.pid,
        "started_at": task.started_at.isoformat(),
        "finished_at": None if task.finished_at is None else task.finished_at.isoformat(),
        "error": _error(task),
        "result": task.result,
    }


def _error(task: TaskRow) -> dict[str, Any] | None:
    return None if task.error_code is None else _failure(task).to_dict()


def _failure(task: TaskRow) -> WordcutError:
    assert task.error_code is not None
    return WordcutError(task.error_code, task.error_message or "", task.error_details)


def _now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)
