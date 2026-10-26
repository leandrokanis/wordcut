import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from wordcut.db import MIGRATIONS, connect, presets
from wordcut.db.presets import PresetFields, PresetRow, SecondsRange
from wordcut.home import Home

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def test_a_new_installation_has_only_the_factory_default_preset(
    connection: sqlite3.Connection,
) -> None:
    [only] = presets.all_presets(connection)

    assert (
        only.name,
        only.is_default,
        only.levels,
        only.duration_allowed,
        only.duration_ideal,
        only.reorder,
        only.protected_words,
        only.instructions,
    ) == (
        "Padrão",
        True,
        {},
        SecondsRange(40, 75),
        SecondsRange(55, 65),
        True,
        ("não", "mas", "se"),
        "",
    )


def fields(name: str = "Estudo bíblico") -> PresetFields:
    return PresetFields(
        name=name,
        levels={"allegory": "strict", "christological": "lenient"},
        duration_allowed=SecondsRange(45, 80),
        duration_ideal=SecondsRange(60, 75),
        reorder=False,
        protected_words=("não", "mas"),
        instructions="Prefira trechos de aplicação.",
    )


def test_an_inserted_preset_is_read_back_by_its_id_with_every_field(
    connection: sqlite3.Connection,
) -> None:
    inserted = presets.insert(connection, fields(), NOW)

    assert presets.by_id(connection, inserted.id) == PresetRow(
        id=inserted.id,
        name="Estudo bíblico",
        is_default=False,
        levels={"allegory": "strict", "christological": "lenient"},
        duration_allowed=SecondsRange(45, 80),
        duration_ideal=SecondsRange(60, 75),
        reorder=False,
        protected_words=("não", "mas"),
        instructions="Prefira trechos de aplicação.",
        created_at=NOW,
        updated_at=NOW,
    )


def test_an_updated_preset_is_read_back_with_the_new_fields_and_update_time(
    connection: sqlite3.Connection,
) -> None:
    inserted = presets.insert(connection, fields(), NOW)
    later = NOW + timedelta(minutes=5)
    changed = replace(fields("Culto da família"), levels={}, reorder=True, instructions="")

    presets.update(connection, inserted.id, changed, later)

    assert presets.by_id(connection, inserted.id) == replace(
        inserted,
        name="Culto da família",
        levels={},
        reorder=True,
        instructions="",
        updated_at=later,
    )


def test_the_database_refuses_a_second_default_preset(connection: sqlite3.Connection) -> None:
    other = presets.insert(connection, fields(), NOW)

    with pytest.raises(sqlite3.IntegrityError), connection:
        presets.set_default_flag(connection, other.id, True, NOW)


def test_the_default_moves_once_the_previous_one_is_cleared(
    connection: sqlite3.Connection,
) -> None:
    [factory] = presets.all_presets(connection)
    other = presets.insert(connection, fields(), NOW)

    with connection:
        presets.set_default_flag(connection, factory.id, False, NOW)
        presets.set_default_flag(connection, other.id, True, NOW)

    flags = [(row.id, row.is_default) for row in presets.all_presets(connection)]
    assert flags == [(factory.id, False), (other.id, True)]


def test_the_database_refuses_a_repeated_preset_name(connection: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError), connection:
        presets.insert(connection, fields("Padrão"), NOW)


def test_a_deleted_preset_is_no_longer_found(connection: sqlite3.Connection) -> None:
    inserted = presets.insert(connection, fields(), NOW)

    presets.delete(connection, inserted.id)

    assert presets.by_id(connection, inserted.id) is None


def test_a_database_of_the_previous_version_gains_the_factory_preset_and_keeps_its_data(
    tmp_path: Path,
) -> None:
    previous = tmp_path / "migrations-0005"
    previous.mkdir()
    for packaged in MIGRATIONS.glob("000[1-5]_*.sql"):
        (previous / packaged.name).write_text(packaged.read_text(encoding="utf-8"))
    home = Home(tmp_path / "home")
    with closing(connect(home, previous)) as old, old:
        old.execute("INSERT INTO settings (key, value) VALUES ('whisper_model', 'medium')")

    with closing(connect(home)) as connection:
        kept = connection.execute("SELECT value FROM settings").fetchall()
        names = [row.name for row in presets.all_presets(connection)]
        version = connection.execute("PRAGMA user_version").fetchone()[0]

    assert (kept, names, version) == ([("medium",)], ["Padrão"], 6)
