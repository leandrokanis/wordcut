"""SQL access to the ``word_fixes`` table (migration 0008), without business rules (ADR-0004).

Writes run in the caller's transaction (``with connection:``).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime


def put(
    connection: sqlite3.Connection, cut_id: int, word_id: int, text: str, now: datetime
) -> None:
    """Make ``text`` the fix of the word in the cut, replacing the one it had."""
    connection.execute(
        "INSERT INTO word_fixes (cut_id, word_id, text, created_at) VALUES (?, ?, ?, ?)"
        " ON CONFLICT (cut_id, word_id) DO UPDATE SET text = excluded.text,"
        " created_at = excluded.created_at",
        (cut_id, word_id, text, now.isoformat()),
    )


def of_cut(connection: sqlite3.Connection, cut_id: int) -> dict[int, str]:
    """The fixes of the cut, by word ID."""
    found = connection.execute(
        "SELECT word_id, text FROM word_fixes WHERE cut_id = ?", (cut_id,)
    ).fetchall()
    return dict(found)


def delete(connection: sqlite3.Connection, cut_id: int, word_id: int) -> None:
    """Remove the fix of the word in the cut, if it has one."""
    connection.execute("DELETE FROM word_fixes WHERE cut_id = ? AND word_id = ?", (cut_id, word_id))


def of_sermon(connection: sqlite3.Connection, sermon_id: int) -> dict[int, dict[int, str]]:
    """The fixes of every cut of the sermon, by cut ID and then by word ID; a cut without
    fixes is left out."""
    found = connection.execute(
        "SELECT word_fixes.cut_id, word_fixes.word_id, word_fixes.text FROM word_fixes"
        " JOIN cuts ON cuts.id = word_fixes.cut_id WHERE cuts.sermon_id = ?",
        (sermon_id,),
    ).fetchall()
    fixes: dict[int, dict[int, str]] = {}
    for cut_id, word_id, text in found:
        fixes.setdefault(cut_id, {})[word_id] = text
    return fixes
