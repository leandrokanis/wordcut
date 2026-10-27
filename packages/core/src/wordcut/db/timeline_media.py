"""SQL access to the ``timeline_media`` table (migration 0012)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TimelineError:
    """Why the last preparation of the timeline failed."""

    code: str
    message: str


@dataclass(frozen=True)
class TimelineRow:
    sermon_id: int
    status: str
    error: TimelineError | None
    updated_at: datetime


def record(
    connection: sqlite3.Connection,
    sermon_id: int,
    status: str,
    now: datetime,
    error: TimelineError | None = None,
) -> None:
    """Set the state of the sermon's timeline, replacing the one it had."""
    code, message = (None, None) if error is None else (error.code, error.message)
    with connection:
        connection.execute(
            "INSERT INTO timeline_media (sermon_id, status, error_code, error_message, updated_at)"
            " VALUES (?, ?, ?, ?, ?) ON CONFLICT (sermon_id) DO UPDATE SET"
            " status = excluded.status, error_code = excluded.error_code,"
            " error_message = excluded.error_message, updated_at = excluded.updated_at",
            (sermon_id, status, code, message, now.isoformat()),
        )


def of_sermon(connection: sqlite3.Connection, sermon_id: int) -> TimelineRow | None:
    found = connection.execute(
        "SELECT sermon_id, status, error_code, error_message, updated_at FROM timeline_media"
        " WHERE sermon_id = ?",
        (sermon_id,),
    ).fetchone()
    if found is None:
        return None
    sermon, status, code, message, updated_at = found
    return TimelineRow(
        sermon_id=sermon,
        status=status,
        error=None if code is None else TimelineError(code, message),
        updated_at=datetime.fromisoformat(updated_at),
    )
