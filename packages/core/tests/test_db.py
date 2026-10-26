import sqlite3
from contextlib import closing
from importlib.metadata import version
from pathlib import Path

import pytest

from wordcut.db import MIGRATIONS, connect
from wordcut.home import Home


def test_data_root_is_wordcut_home_when_it_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORDCUT_HOME", str(tmp_path / "dados"))

    assert Home.from_environment().root == tmp_path / "dados"


def test_data_root_defaults_to_the_user_data_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("WORDCUT_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert Home.from_environment().root == tmp_path / ".local/share/wordcut"


def test_first_connection_creates_the_data_folder_private_to_the_user(tmp_path: Path) -> None:
    home = Home(tmp_path / "dados" / "wordcut")

    connect(home).close()

    assert home.root.stat().st_mode & 0o777 == 0o700


def latest_packaged_migration() -> int:
    return max(int(path.name.split("_")[0]) for path in MIGRATIONS.glob("*.sql"))


def schema_version(connection: sqlite3.Connection) -> int:
    version: int = connection.execute("PRAGMA user_version").fetchone()[0]
    return version


def test_first_connection_applies_every_packaged_migration(tmp_path: Path) -> None:
    with closing(connect(Home(tmp_path))) as connection:
        assert schema_version(connection) == latest_packaged_migration() >= 1


def test_new_database_records_the_version_that_created_it(tmp_path: Path) -> None:
    with closing(connect(Home(tmp_path))) as connection:
        row = connection.execute("SELECT value FROM app_info WHERE key = 'created_by'").fetchone()

    assert row == (f"wordcut-core {version('wordcut-core')}",)


def test_connection_enforces_foreign_keys_and_shares_the_file_with_other_processes(
    tmp_path: Path,
) -> None:
    with closing(connect(Home(tmp_path))) as connection:
        settings = tuple(
            connection.execute(f"PRAGMA {name}").fetchone()[0]
            for name in ("foreign_keys", "journal_mode", "busy_timeout")
        )

    assert settings == (1, "wal", 5000)


def test_reopening_the_database_keeps_its_data_and_schema_version(tmp_path: Path) -> None:
    home = Home(tmp_path)
    with closing(connect(home)) as connection, connection:
        connection.execute("INSERT INTO app_info (key, value) VALUES ('nota', 'mantida')")

    with closing(connect(home)) as connection:
        kept = connection.execute("SELECT value FROM app_info WHERE key = 'nota'").fetchone()
        assert (kept, schema_version(connection)) == (("mantida",), latest_packaged_migration())


def test_database_from_before_the_migrations_is_migrated_without_losing_data(
    tmp_path: Path,
) -> None:
    home = Home(tmp_path)
    with closing(sqlite3.connect(home.database)) as old, old:
        old.execute("CREATE TABLE anotacao (texto TEXT)")
        old.execute("INSERT INTO anotacao VALUES ('anterior')")

    with closing(connect(home)) as connection:
        kept = connection.execute("SELECT texto FROM anotacao").fetchall()
        assert (kept, schema_version(connection)) == ([("anterior",)], latest_packaged_migration())


def migrations_with(tmp_path: Path, name: str, script: str) -> Path:
    folder = tmp_path / "migrations"
    folder.mkdir()
    for packaged in MIGRATIONS.glob("*.sql"):
        (folder / packaged.name).write_text(packaged.read_text(encoding="utf-8"))
    (folder / name).write_text(script)
    return folder


def test_only_pending_migrations_are_applied_to_an_older_schema(tmp_path: Path) -> None:
    home = Home(tmp_path / "home")
    with closing(connect(home)) as connection, connection:
        connection.execute("INSERT INTO app_info (key, value) VALUES ('nota', 'mantida')")
    newer = migrations_with(
        tmp_path, "9001_note_author.sql", "ALTER TABLE app_info ADD COLUMN author TEXT;"
    )

    with closing(connect(home, newer)) as connection:
        row = connection.execute("SELECT value, author FROM app_info WHERE key = 'nota'").fetchone()
        assert (row, schema_version(connection)) == (("mantida", None), 9001)


def test_failing_migration_leaves_neither_partial_schema_nor_a_new_version(
    tmp_path: Path,
) -> None:
    home = Home(tmp_path / "home")
    connect(home).close()
    broken = migrations_with(
        tmp_path,
        "9001_broken.sql",
        "CREATE TABLE meio_caminho (id INTEGER);\nINSERT INTO tabela_inexistente VALUES (1);",
    )

    with pytest.raises(sqlite3.OperationalError):
        connect(home, broken)

    with closing(connect(home)) as connection:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE name = 'meio_caminho'"
        ).fetchall()
        assert (tables, schema_version(connection)) == ([], latest_packaged_migration())
