"""SQL access to the ``cuts`` table (migration 0007), without business rules (ADR-0004).

Writes run in the caller's transaction (``with connection:``).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

COLUMNS = (
    "id, sermon_id, status, title, segments, range_start_word, range_end_word, source,"
    " preset_id, edited, caption, render_options, created_at, updated_at"
)


@dataclass(frozen=True)
class Segment:
    """Words ``from_word`` to ``to_word`` of the sermon, by word ID, inclusive."""

    from_word: int
    to_word: int


@dataclass(frozen=True)
class NewCut:
    status: str
    title: str
    segments: tuple[Segment, ...]
    range_start_word: int
    range_end_word: int
    source: str
    preset_id: int | None


@dataclass(frozen=True)
class CutRow:
    id: int
    sermon_id: int
    status: str
    title: str
    segments: tuple[Segment, ...]
    range_start_word: int
    range_end_word: int
    source: str
    preset_id: int | None
    edited: bool
    caption: dict[str, Any] | None
    render_options: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


def insert_many(
    connection: sqlite3.Connection, sermon_id: int, new: Sequence[NewCut], now: datetime
) -> None:
    """Add the cuts to the sermon, in the order given."""
    connection.executemany(
        "INSERT INTO cuts (sermon_id, status, title, segments, range_start_word,"
        " range_end_word, source, preset_id, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                sermon_id,
                cut.status,
                cut.title,
                _segments_json(cut.segments),
                cut.range_start_word,
                cut.range_end_word,
                cut.source,
                cut.preset_id,
                now.isoformat(),
                now.isoformat(),
            )
            for cut in new
        ],
    )


def of_sermon(connection: sqlite3.Connection, sermon_id: int) -> list[CutRow]:
    """The cuts of the sermon in the order they were added."""
    found = connection.execute(
        f"SELECT {COLUMNS} FROM cuts WHERE sermon_id = ? ORDER BY id", (sermon_id,)
    ).fetchall()
    return [_row(values) for values in found]


def counts_of(connection: sqlite3.Connection, sermon_id: int) -> dict[str, int]:
    """How many cuts of the sermon are in each state; a state without cuts is left out."""
    found = connection.execute(
        "SELECT status, COUNT(*) FROM cuts WHERE sermon_id = ? GROUP BY status", (sermon_id,)
    ).fetchall()
    return {status: count for status, count in found}


def delete_of(connection: sqlite3.Connection, sermon_id: int) -> None:
    """Remove every cut of the sermon."""
    connection.execute("DELETE FROM cuts WHERE sermon_id = ?", (sermon_id,))


def _segments_json(segments: Sequence[Segment]) -> str:
    return json.dumps(
        [{"from_word": segment.from_word, "to_word": segment.to_word} for segment in segments]
    )


def _segments(text: str) -> tuple[Segment, ...]:
    return tuple(Segment(item["from_word"], item["to_word"]) for item in json.loads(text))


def _json_or_none(text: str | None) -> dict[str, Any] | None:
    return None if text is None else dict(json.loads(text))


def _row(values: tuple[Any, ...]) -> CutRow:
    (
        cut_id,
        sermon_id,
        status,
        title,
        segments,
        range_start_word,
        range_end_word,
        source,
        preset_id,
        edited,
        caption,
        render_options,
        created_at,
        updated_at,
    ) = values
    return CutRow(
        id=cut_id,
        sermon_id=sermon_id,
        status=status,
        title=title,
        segments=_segments(segments),
        range_start_word=range_start_word,
        range_end_word=range_end_word,
        source=source,
        preset_id=preset_id,
        edited=bool(edited),
        caption=_json_or_none(caption),
        render_options=_json_or_none(render_options),
        created_at=datetime.fromisoformat(created_at),
        updated_at=datetime.fromisoformat(updated_at),
    )
