"""SQL access to the ``renders`` table (migration 0009), without business rules (ADR-0004).

Writes run in the caller's transaction (``with connection:``).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

COLUMNS = "id, cut_id, path, duration, options, created_at"


@dataclass(frozen=True)
class NewRender:
    cut_id: int
    path: str
    duration: float
    options: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class RenderRow:
    id: int
    cut_id: int
    path: str
    duration: float
    options: dict[str, Any]
    created_at: datetime


def insert(connection: sqlite3.Connection, new: NewRender) -> int:
    """Record the export and give its ID."""
    cursor = connection.execute(
        "INSERT INTO renders (cut_id, path, duration, options, created_at) VALUES (?, ?, ?, ?, ?)",
        (new.cut_id, new.path, new.duration, json.dumps(new.options), new.created_at.isoformat()),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def set_path(connection: sqlite3.Connection, render_id: int, path: str) -> None:
    connection.execute("UPDATE renders SET path = ? WHERE id = ?", (path, render_id))


def by_id(connection: sqlite3.Connection, render_id: int) -> RenderRow | None:
    found = connection.execute(
        f"SELECT {COLUMNS} FROM renders WHERE id = ?", (render_id,)
    ).fetchone()
    return None if found is None else _row(found)


def of_cut(connection: sqlite3.Connection, cut_id: int) -> list[RenderRow]:
    """The exports of the cut, the oldest first."""
    found = connection.execute(
        f"SELECT {COLUMNS} FROM renders WHERE cut_id = ? ORDER BY id", (cut_id,)
    ).fetchall()
    return [_row(values) for values in found]


def _row(values: tuple[Any, ...]) -> RenderRow:
    render_id, cut_id, path, duration, options, created_at = values
    return RenderRow(
        id=render_id,
        cut_id=cut_id,
        path=path,
        duration=duration,
        options=dict(json.loads(options)),
        created_at=datetime.fromisoformat(created_at),
    )
