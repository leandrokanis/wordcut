import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from wordcut.db import MIGRATIONS, connect, sermons
from wordcut.db.sermons import NewSermon, SermonRow
from wordcut.home import Home

CREATED_AT = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def new_sermon(
    youtube_id: str = "Ab3_x-9QzLk", service_date: date = date(2026, 10, 18)
) -> NewSermon:
    return NewSermon(
        youtube_id=youtube_id,
        url=f"https://youtu.be/{youtube_id}",
        title="Culto de domingo",
        service_date=service_date,
        live_duration=7718.0,
        live_finished=True,
        created_at=CREATED_AT,
    )


def test_inserted_sermon_is_read_back_by_its_id_with_every_field(
    connection: sqlite3.Connection,
) -> None:
    inserted = sermons.insert(connection, new_sermon())

    assert sermons.by_id(connection, inserted.id) == SermonRow(
        id=inserted.id,
        youtube_id="Ab3_x-9QzLk",
        url="https://youtu.be/Ab3_x-9QzLk",
        title="Culto de domingo",
        service_date=date(2026, 10, 18),
        live_duration=7718.0,
        live_finished=True,
        status="created",
        live_start=None,
        live_end=None,
        created_at=CREATED_AT,
        updated_at=CREATED_AT,
    )


def test_recorded_range_is_read_back_with_its_status_and_update_time(
    connection: sqlite3.Connection,
) -> None:
    inserted = sermons.insert(connection, new_sermon())
    updated_at = CREATED_AT + timedelta(minutes=5)

    sermons.update_range(connection, inserted.id, 3730.0, 6510.0, "trimmed", updated_at)

    assert sermons.by_id(connection, inserted.id) == replace(
        inserted, live_start=3730.0, live_end=6510.0, status="trimmed", updated_at=updated_at
    )


def test_inserted_sermon_is_found_by_its_video_id(connection: sqlite3.Connection) -> None:
    inserted = sermons.insert(connection, new_sermon())

    assert sermons.by_youtube_id(connection, "Ab3_x-9QzLk") == inserted


def test_second_sermon_of_the_same_video_is_refused(connection: sqlite3.Connection) -> None:
    sermons.insert(connection, new_sermon())

    with pytest.raises(sqlite3.IntegrityError):
        sermons.insert(connection, new_sermon())


@pytest.mark.parametrize("status", ["created", "trimmed", "processing", "processed", "failed"])
def test_database_accepts_each_sermon_status(connection: sqlite3.Connection, status: str) -> None:
    inserted = sermons.insert(connection, new_sermon())
    with connection:
        connection.execute("UPDATE sermons SET status = ? WHERE id = ?", (status, inserted.id))

    assert sermons.by_id(connection, inserted.id) == replace(inserted, status=status)


def test_database_refuses_a_status_outside_the_sermon_states(
    connection: sqlite3.Connection,
) -> None:
    inserted = sermons.insert(connection, new_sermon())

    with pytest.raises(sqlite3.IntegrityError), connection:
        connection.execute("UPDATE sermons SET status = 'archived' WHERE id = ?", (inserted.id,))


def test_unknown_id_or_video_finds_no_sermon(connection: sqlite3.Connection) -> None:
    assert (sermons.by_id(connection, 999), sermons.by_youtube_id(connection, "Zz9_x-9QzLk")) == (
        None,
        None,
    )


def test_sermons_come_newest_service_first_and_the_later_one_first_on_the_same_day(
    connection: sqlite3.Connection,
) -> None:
    oldest = sermons.insert(connection, new_sermon("Aaaaaaaaaa1", date(2026, 10, 11)))
    same_day_first = sermons.insert(connection, new_sermon("Aaaaaaaaaa2", date(2026, 10, 18)))
    newest = sermons.insert(connection, new_sermon("Aaaaaaaaaa3", date(2026, 10, 25)))
    same_day_second = sermons.insert(connection, new_sermon("Aaaaaaaaaa4", date(2026, 10, 18)))

    assert sermons.newest_first(connection) == [newest, same_day_second, same_day_first, oldest]


def test_listing_with_a_status_keeps_only_the_sermons_in_that_state(
    connection: sqlite3.Connection,
) -> None:
    created = sermons.insert(connection, new_sermon("Aaaaaaaaaa1"))
    trimmed = sermons.insert(connection, new_sermon("Aaaaaaaaaa2"))
    with connection:
        connection.execute("UPDATE sermons SET status = 'trimmed' WHERE id = ?", (trimmed.id,))

    assert sermons.newest_first(connection, status="created") == [created]


def schema_version(connection: sqlite3.Connection) -> int:
    version: int = connection.execute("PRAGMA user_version").fetchone()[0]
    return version


def test_new_database_has_schema_version_2_with_an_empty_sermons_table(tmp_path: Path) -> None:
    with closing(connect(Home(tmp_path))) as opened:
        assert (schema_version(opened) >= 2, sermons.newest_first(opened)) == (True, [])


def test_database_at_schema_version_1_gains_the_sermons_table_and_keeps_its_data(
    tmp_path: Path,
) -> None:
    home = Home(tmp_path / "home")
    only_base = tmp_path / "migrations"
    only_base.mkdir()
    (only_base / "0001_base.sql").write_text((MIGRATIONS / "0001_base.sql").read_text())
    with closing(connect(home, only_base)) as old, old:
        old.execute("INSERT INTO app_info (key, value) VALUES ('nota', 'mantida')")

    with closing(connect(home)) as opened:
        kept = opened.execute("SELECT value FROM app_info WHERE key = 'nota'").fetchone()
        inserted = sermons.insert(opened, new_sermon())
        assert (schema_version(opened) >= 2, kept, sermons.newest_first(opened)) == (
            True,
            ("mantida",),
            [inserted],
        )
