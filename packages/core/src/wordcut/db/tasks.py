"""SQL access to the ``tasks`` table (migration 0003)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

COLUMNS = (
    "id, kind, resource_type, resource_id, params, status, progress, progress_message, pid,"
    " host, started_at, finished_at, error_code, error_message, error_details, result"
)


@dataclass(frozen=True)
class NewTask:
    kind: str
    resource_type: str
    resource_id: int
    params: dict[str, Any]
    pid: int
    host: str
    started_at: datetime


@dataclass(frozen=True)
class TaskRow:
    id: int
    kind: str
    resource_type: str
    resource_id: int
    params: dict[str, Any]
    status: str
    progress: float
    progress_message: str | None
    pid: int
    host: str
    started_at: datetime
    finished_at: datetime | None
    error_code: str | None
    error_message: str | None
    error_details: dict[str, Any] | None
    result: dict[str, Any] | None


def insert(connection: sqlite3.Connection, task: NewTask) -> TaskRow:
    """Record ``task`` as ``running``."""
    with connection:
        cursor = connection.execute(
            "INSERT INTO tasks (kind, resource_type, resource_id, params, status, pid, host,"
            " started_at) VALUES (?, ?, ?, ?, 'running', ?, ?, ?)",
            (
                task.kind,
                task.resource_type,
                task.resource_id,
                json.dumps(task.params),
                task.pid,
                task.host,
                task.started_at.isoformat(),
            ),
        )
    assert cursor.lastrowid is not None
    row = by_id(connection, cursor.lastrowid)
    assert row is not None
    return row


def set_pid(connection: sqlite3.Connection, task_id: int, pid: int) -> None:
    with connection:
        connection.execute("UPDATE tasks SET pid = ? WHERE id = ?", (pid, task_id))


def record_progress(
    connection: sqlite3.Connection, task_id: int, progress: float, message: str
) -> None:
    with connection:
        connection.execute(
            "UPDATE tasks SET progress = ?, progress_message = ? WHERE id = ?",
            (progress, message, task_id),
        )


def finish_succeeded(
    connection: sqlite3.Connection, task_id: int, result: dict[str, Any], finished_at: datetime
) -> None:
    with connection:
        connection.execute(
            "UPDATE tasks SET status = 'succeeded', progress = 1, result = ?, finished_at = ?"
            " WHERE id = ? AND status = 'running'",
            (json.dumps(result), finished_at.isoformat(), task_id),
        )


def finish_failed(
    connection: sqlite3.Connection,
    task_id: int,
    code: str,
    message: str,
    details: dict[str, Any] | None,
    finished_at: datetime,
) -> None:
    with connection:
        connection.execute(
            "UPDATE tasks SET status = 'failed', error_code = ?, error_message = ?,"
            " error_details = ?, finished_at = ? WHERE id = ? AND status = 'running'",
            (
                code,
                message,
                None if details is None else json.dumps(details),
                finished_at.isoformat(),
                task_id,
            ),
        )


def by_id(connection: sqlite3.Connection, task_id: int) -> TaskRow | None:
    found = connection.execute(f"SELECT {COLUMNS} FROM tasks WHERE id = ?", (task_id,))
    values = found.fetchone()
    return None if values is None else _row(values)


def newest_first(
    connection: sqlite3.Connection, status: str | None = None, kind: str | None = None
) -> list[TaskRow]:
    """Tasks with the latest start first, only those in ``status`` and of ``kind`` when given."""
    found = connection.execute(
        f"SELECT {COLUMNS} FROM tasks WHERE (? IS NULL OR status = ?) AND (? IS NULL OR kind = ?)"
        " ORDER BY started_at DESC, id DESC",
        (status, status, kind, kind),
    ).fetchall()
    return [_row(values) for values in found]


def _row(values: tuple[Any, ...]) -> TaskRow:
    (
        task_id,
        kind,
        resource_type,
        resource_id,
        params,
        status,
        progress,
        progress_message,
        pid,
        host,
        started_at,
        finished_at,
        error_code,
        error_message,
        error_details,
        result,
    ) = values
    return TaskRow(
        id=task_id,
        kind=kind,
        resource_type=resource_type,
        resource_id=resource_id,
        params=json.loads(params),
        status=status,
        progress=progress,
        progress_message=progress_message,
        pid=pid,
        host=host,
        started_at=datetime.fromisoformat(started_at),
        finished_at=_moment(finished_at),
        error_code=error_code,
        error_message=error_message,
        error_details=_json(error_details),
        result=_json(result),
    )


def _moment(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _json(value: str | None) -> Any:
    return None if value is None else json.loads(value)
