"""SQL access to the ``sermons`` table (migrations 0002, 0004 and 0007)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

COLUMNS = (
    "id, youtube_id, url, title, service_date, live_duration, live_finished, status,"
    " live_start, live_end, created_at, updated_at, sermon_start, sermon_end, video_path,"
    " processed_at, suggestion_error_code, suggestion_error_message"
)


@dataclass(frozen=True)
class SuggestionError:
    """Why the last cut suggestion of the sermon failed."""

    code: str
    message: str


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
    sermon_start: float | None = None
    sermon_end: float | None = None
    video_path: str | None = None
    processed_at: datetime | None = None
    suggestion_error: SuggestionError | None = None


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


def update_range(
    connection: sqlite3.Connection,
    sermon_id: int,
    live_start: float,
    live_end: float,
    status: str,
    updated_at: datetime,
) -> None:
    """Record the borders of the sermon in the live and the status they lead to."""
    with connection:
        connection.execute(
            "UPDATE sermons SET live_start = ?, live_end = ?, status = ?, updated_at = ?"
            " WHERE id = ?",
            (live_start, live_end, status, updated_at.isoformat(), sermon_id),
        )


def set_status(
    connection: sqlite3.Connection, sermon_id: int, status: str, updated_at: datetime
) -> None:
    """Change the status of the sermon, in the caller's transaction."""
    connection.execute(
        "UPDATE sermons SET status = ?, updated_at = ? WHERE id = ?",
        (status, updated_at.isoformat(), sermon_id),
    )


def update_live(
    connection: sqlite3.Connection,
    sermon_id: int,
    live_duration: float | None,
    live_finished: bool,
    updated_at: datetime,
) -> None:
    with connection:
        connection.execute(
            "UPDATE sermons SET live_duration = ?, live_finished = ?, updated_at = ? WHERE id = ?",
            (live_duration, live_finished, updated_at.isoformat(), sermon_id),
        )


def record_processed(
    connection: sqlite3.Connection,
    sermon_id: int,
    sermon_start: float,
    sermon_end: float,
    video_path: str,
    processed_at: datetime,
) -> None:
    """Mark the sermon ``processed``, in the caller's transaction, with its borders fitted to
    the words (live time) and its video (``video_path``, relative to the data folder)."""
    connection.execute(
        "UPDATE sermons SET status = 'processed', sermon_start = ?, sermon_end = ?,"
        " video_path = ?, processed_at = ?, updated_at = ? WHERE id = ?",
        (
            sermon_start,
            sermon_end,
            video_path,
            processed_at.isoformat(),
            processed_at.isoformat(),
            sermon_id,
        ),
    )


def record_suggestion_error(
    connection: sqlite3.Connection, sermon_id: int, error: SuggestionError | None
) -> None:
    """Keep why the last suggestion failed, or ``None`` when it succeeded, in the caller's
    transaction."""
    connection.execute(
        "UPDATE sermons SET suggestion_error_code = ?, suggestion_error_message = ? WHERE id = ?",
        (
            None if error is None else error.code,
            None if error is None else error.message,
            sermon_id,
        ),
    )


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
        sermon_start,
        sermon_end,
        video_path,
        processed_at,
        suggestion_error_code,
        suggestion_error_message,
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
        sermon_start=sermon_start,
        sermon_end=sermon_end,
        video_path=video_path,
        processed_at=None if processed_at is None else datetime.fromisoformat(processed_at),
        suggestion_error=(
            None
            if suggestion_error_code is None
            else SuggestionError(suggestion_error_code, suggestion_error_message)
        ),
    )
