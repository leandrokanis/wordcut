"""SQL access to the ``presets`` table (migration 0006), without business rules (ADR-0004)."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

COLUMNS = (
    "id, name, is_default, levels, duration_allowed_min, duration_allowed_max,"
    " duration_ideal_min, duration_ideal_max, reorder, protected_words, instructions,"
    " created_at, updated_at"
)


@dataclass(frozen=True)
class SecondsRange:
    """A duration range in whole seconds."""

    min: int
    max: int


@dataclass(frozen=True)
class PresetFields:
    """What the administrator edits in a preset."""

    name: str
    levels: dict[str, str]
    duration_allowed: SecondsRange
    duration_ideal: SecondsRange
    reorder: bool
    protected_words: tuple[str, ...]
    instructions: str


@dataclass(frozen=True)
class PresetRow:
    id: int
    name: str
    is_default: bool
    # As stored: the service completes and filters it against the catalog.
    levels: dict[str, str]
    duration_allowed: SecondsRange
    duration_ideal: SecondsRange
    reorder: bool
    protected_words: tuple[str, ...]
    instructions: str
    created_at: datetime
    updated_at: datetime


def insert(connection: sqlite3.Connection, fields: PresetFields, now: datetime) -> PresetRow:
    """Insert a preset that is not the default, in the caller's transaction."""
    cursor = connection.execute(
        "INSERT INTO presets (name, levels, duration_allowed_min, duration_allowed_max,"
        " duration_ideal_min, duration_ideal_max, reorder, protected_words, instructions,"
        " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (*_values(fields), now.isoformat(), now.isoformat()),
    )
    assert cursor.lastrowid is not None
    row = by_id(connection, cursor.lastrowid)
    assert row is not None
    return row


def update(
    connection: sqlite3.Connection, preset_id: int, fields: PresetFields, now: datetime
) -> None:
    """Replace the editable fields of the preset, in the caller's transaction."""
    connection.execute(
        "UPDATE presets SET name = ?, levels = ?, duration_allowed_min = ?,"
        " duration_allowed_max = ?, duration_ideal_min = ?, duration_ideal_max = ?,"
        " reorder = ?, protected_words = ?, instructions = ?, updated_at = ? WHERE id = ?",
        (*_values(fields), now.isoformat(), preset_id),
    )


def set_default_flag(
    connection: sqlite3.Connection, preset_id: int, is_default: bool, now: datetime
) -> None:
    """Mark or clear the preset as the default, in the caller's transaction.

    The database allows one default at most: clear the previous one first.
    """
    connection.execute(
        "UPDATE presets SET is_default = ?, updated_at = ? WHERE id = ?",
        (is_default, now.isoformat(), preset_id),
    )


def delete(connection: sqlite3.Connection, preset_id: int) -> None:
    """Delete the preset, in the caller's transaction."""
    connection.execute("DELETE FROM presets WHERE id = ?", (preset_id,))


def by_id(connection: sqlite3.Connection, preset_id: int) -> PresetRow | None:
    values = connection.execute(
        f"SELECT {COLUMNS} FROM presets WHERE id = ?", (preset_id,)
    ).fetchone()
    return None if values is None else _row(values)


def by_name(connection: sqlite3.Connection, name: str) -> PresetRow | None:
    values = connection.execute(f"SELECT {COLUMNS} FROM presets WHERE name = ?", (name,)).fetchone()
    return None if values is None else _row(values)


def default(connection: sqlite3.Connection) -> PresetRow | None:
    values = connection.execute(f"SELECT {COLUMNS} FROM presets WHERE is_default = 1").fetchone()
    return None if values is None else _row(values)


def all_presets(connection: sqlite3.Connection) -> list[PresetRow]:
    found = connection.execute(f"SELECT {COLUMNS} FROM presets ORDER BY id").fetchall()
    return [_row(values) for values in found]


def _values(fields: PresetFields) -> tuple[Any, ...]:
    return (
        fields.name,
        json.dumps(fields.levels, ensure_ascii=False),
        fields.duration_allowed.min,
        fields.duration_allowed.max,
        fields.duration_ideal.min,
        fields.duration_ideal.max,
        fields.reorder,
        json.dumps(list(fields.protected_words), ensure_ascii=False),
        fields.instructions,
    )


def _row(values: tuple[Any, ...]) -> PresetRow:
    (
        preset_id,
        name,
        is_default,
        levels,
        allowed_min,
        allowed_max,
        ideal_min,
        ideal_max,
        reorder,
        protected_words,
        instructions,
        created_at,
        updated_at,
    ) = values
    return PresetRow(
        id=preset_id,
        name=name,
        is_default=bool(is_default),
        levels=json.loads(levels),
        duration_allowed=SecondsRange(allowed_min, allowed_max),
        duration_ideal=SecondsRange(ideal_min, ideal_max),
        reorder=bool(reorder),
        protected_words=tuple(json.loads(protected_words)),
        instructions=instructions,
        created_at=datetime.fromisoformat(created_at),
        updated_at=datetime.fromisoformat(updated_at),
    )
