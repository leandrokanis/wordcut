"""The SQLite database in the data folder, created and migrated on connection (ADR-0005)."""

from __future__ import annotations

import sqlite3
from importlib.metadata import version
from pathlib import Path

from wordcut.home import Home

MIGRATIONS = Path(__file__).parent / "migrations"

# The CLI and the API write to the same file; a writer waits this long for the other one.
BUSY_TIMEOUT_MS = 5000


def connect(home: Home, migrations: Path = MIGRATIONS) -> sqlite3.Connection:
    """Open the database of ``home``, creating it and applying pending migrations.

    Migrations are ``NNNN_name.sql`` files in ``migrations``, applied in order, each in its
    own transaction; ``PRAGMA user_version`` holds the number of the last one applied. A
    migration file must not contain ``BEGIN`` or ``COMMIT``: it would end that transaction
    early and leave a partial schema behind on failure.
    """
    home.ensure()
    is_new = not home.database.exists()
    connection = sqlite3.connect(home.database)
    try:
        _configure(connection)
        _migrate(connection, migrations)
        if is_new:
            _record_creator(connection)
    except BaseException:
        connection.close()
        raise
    return connection


def _configure(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")


def _migrate(connection: sqlite3.Connection, migrations: Path) -> None:
    current: int = connection.execute("PRAGMA user_version").fetchone()[0]
    for number, script in _pending(migrations, current):
        _apply(connection, number, script)


def _pending(migrations: Path, current: int) -> list[tuple[int, str]]:
    numbered = sorted((int(path.name.split("_")[0]), path) for path in migrations.glob("*.sql"))
    return [
        (number, path.read_text(encoding="utf-8")) for number, path in numbered if number > current
    ]


def _apply(connection: sqlite3.Connection, number: int, script: str) -> None:
    # executescript runs the script as written, so the transaction is part of the script
    # and is undone here when a statement in the middle fails.
    try:
        connection.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {number};\nCOMMIT;")
    except sqlite3.Error:
        if connection.in_transaction:
            connection.execute("ROLLBACK")
        raise


def _record_creator(connection: sqlite3.Connection) -> None:
    with connection:
        connection.execute(
            "INSERT INTO app_info (key, value) VALUES ('created_by', ?)",
            (f"wordcut-core {version('wordcut-core')}",),
        )
