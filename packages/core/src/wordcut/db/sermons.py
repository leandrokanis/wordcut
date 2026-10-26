"""SQL access to the ``sermons`` table (migration 0002)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

COLUMNS = (
    "id, youtube_id, url, title, service_date, live_duration, live_finished, status,"
    " live_start, live_end, created_at, updated_at"
)


@dataclass(frozen=True)
class NewSermon:
    youtube_id: str
    url: str
    title: str
    service_date: date
    live_duration: float | None
    live_finished: bool
    created_at: datetime


@dataclass(frozen=True)
class SermonRow:
    id: int
    youtube_id: str
    url: str
    title: str
    service_date: date
    live_duration: float | None
    live_finished: bool
    status: str
    live_start: float | None
    live_end: float | None
    created_at: datetime
    updated_at: datetime


def insert(connection: sqlite3.Connection, sermon: NewSermon) -> SermonRow:
    created_at = sermon.created_at.isoformat()
    with connection:
        cursor = connection.execute(
            "INSERT INTO sermons (youtube_id, url, title, service_date, live_duration,"
            " live_finished, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sermon.youtube_id,
                sermon.url,
                sermon.title,
                sermon.service_date.isoformat(),
                sermon.live_duration,
                sermon.live_finished,
                created_at,
                created_at,
            ),
        )
    row = by_id(connection, _inserted_id(cursor))
    assert row is not None
    return row


def by_id(connection: sqlite3.Connection, sermon_id: int) -> SermonRow | None:
    return _one(connection, "id = ?", sermon_id)


def by_youtube_id(connection: sqlite3.Connection, youtube_id: str) -> SermonRow | None:
    return _one(connection, "youtube_id = ?", youtube_id)


def newest_first(connection: sqlite3.Connection, status: str | None = None) -> list[SermonRow]:
    """Sermons with the latest service first, only those in ``status`` when given."""
    found = connection.execute(
        f"SELECT {COLUMNS} FROM sermons WHERE ? IS NULL OR status = ?"
        " ORDER BY service_date DESC, id DESC",
        (status, status),
    ).fetchall()
    return [_row(values) for values in found]


def _one(connection: sqlite3.Connection, condition: str, value: object) -> SermonRow | None:
    found = connection.execute(f"SELECT {COLUMNS} FROM sermons WHERE {condition}", (value,))
    values = found.fetchone()
    return None if values is None else _row(values)


def _inserted_id(cursor: sqlite3.Cursor) -> int:
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def _row(values: tuple[Any, ...]) -> SermonRow:
    (
        sermon_id,
        youtube_id,
        url,
        title,
        service_date,
        live_duration,
        live_finished,
        status,
        live_start,
        live_end,
        created_at,
        updated_at,
    ) = values
    return SermonRow(
        id=sermon_id,
        youtube_id=youtube_id,
        url=url,
        title=title,
        service_date=date.fromisoformat(service_date),
        live_duration=live_duration,
        live_finished=bool(live_finished),
        status=status,
        live_start=live_start,
        live_end=live_end,
        created_at=datetime.fromisoformat(created_at),
        updated_at=datetime.fromisoformat(updated_at),
    )
