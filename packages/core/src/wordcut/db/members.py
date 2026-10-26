"""SQL access to the ``members`` table (migration 0010), without business rules (ADR-0004)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

COLUMNS = "email, role, created_at, updated_at"


@dataclass(frozen=True)
class MemberRow:
    email: str
    role: str
    created_at: datetime
    updated_at: datetime


def insert(connection: sqlite3.Connection, email: str, role: str, now: datetime) -> MemberRow:
    """Insert a member, in the caller's transaction."""
    connection.execute(
        "INSERT INTO members (email, role, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (email, role, now.isoformat(), now.isoformat()),
    )
    row = by_email(connection, email)
    assert row is not None
    return row


def update_role(connection: sqlite3.Connection, email: str, role: str, now: datetime) -> None:
    """Change the role of the member, in the caller's transaction."""
    connection.execute(
        "UPDATE members SET role = ?, updated_at = ? WHERE email = ?",
        (role, now.isoformat(), email),
    )


def delete(connection: sqlite3.Connection, email: str) -> None:
    """Delete the member, in the caller's transaction."""
    connection.execute("DELETE FROM members WHERE email = ?", (email,))


def by_email(connection: sqlite3.Connection, email: str) -> MemberRow | None:
    values = connection.execute(
        f"SELECT {COLUMNS} FROM members WHERE email = ?", (email,)
    ).fetchone()
    return None if values is None else _row(values)


def count_with_role(connection: sqlite3.Connection, role: str) -> int:
    count: int = connection.execute(
        "SELECT count(*) FROM members WHERE role = ?", (role,)
    ).fetchone()[0]
    return count


def all_members(connection: sqlite3.Connection) -> list[MemberRow]:
    found = connection.execute(f"SELECT {COLUMNS} FROM members ORDER BY email").fetchall()
    return [_row(values) for values in found]


def _row(values: tuple[Any, ...]) -> MemberRow:
    email, role, created_at, updated_at = values
    return MemberRow(
        email=email,
        role=role,
        created_at=datetime.fromisoformat(created_at),
        updated_at=datetime.fromisoformat(updated_at),
    )
