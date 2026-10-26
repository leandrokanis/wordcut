import sqlite3
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import MIGRATIONS, connect, cuts, presets, sermons, transcripts
from wordcut.db.cuts import CutRow, NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.home import Home
from wordcut.service.presets import create_preset, delete_preset
from wordcut.transcript import Word

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def new_sermon(youtube_id: str = "Ab3_x-9QzLk") -> NewSermon:
    return NewSermon(
        youtube_id=youtube_id,
        url=f"https://youtu.be/{youtube_id}",
        title="Culto de domingo",
        service_date=date(2026, 10, 18),
        live_duration=7718.0,
        live_finished=True,
        created_at=NOW,
    )


def default_preset_id(connection: sqlite3.Connection) -> int:
    row = presets.default(connection)
    assert row is not None
    return row.id


def new_cut(
    title: str = "Graça que alcança", status: str = "suggested", preset_id: int | None = None
) -> NewCut:
    return NewCut(
        status=status,
        title=title,
        segments=(Segment(120, 135), Segment(90, 99)),
        range_start_word=90,
        range_end_word=135,
        source="llm",
        preset_id=preset_id,
    )


def store(connection: sqlite3.Connection, sermon_id: int, *new: NewCut) -> None:
    with connection:
        cuts.insert_many(connection, sermon_id, new, NOW)


def test_stored_cuts_are_read_back_with_every_field_in_insertion_order(
    connection: sqlite3.Connection,
) -> None:
    sermon = sermons.insert(connection, new_sermon())
    preset_id = default_preset_id(connection)

    store(connection, sermon.id, new_cut("Primeiro", preset_id=preset_id), new_cut("Segundo"))

    found = cuts.of_sermon(connection, sermon.id)
    assert found == [
        CutRow(
            id=found[0].id,
            sermon_id=sermon.id,
            status="suggested",
            title="Primeiro",
            segments=(Segment(120, 135), Segment(90, 99)),
            range_start_word=90,
            range_end_word=135,
            source="llm",
            preset_id=preset_id,
            edited=False,
            caption=None,
            render_options=None,
            created_at=NOW,
            updated_at=NOW,
        ),
        CutRow(
            id=found[1].id,
            sermon_id=sermon.id,
            status="suggested",
            title="Segundo",
            segments=(Segment(120, 135), Segment(90, 99)),
            range_start_word=90,
            range_end_word=135,
            source="llm",
            preset_id=None,
            edited=False,
            caption=None,
            render_options=None,
            created_at=NOW,
            updated_at=NOW,
        ),
    ]


def test_counts_tell_how_many_cuts_of_the_sermon_are_in_each_state(
    connection: sqlite3.Connection,
) -> None:
    sermon = sermons.insert(connection, new_sermon("Aaaaaaaaaa1"))
    other = sermons.insert(connection, new_sermon("Aaaaaaaaaa2"))
    store(
        connection,
        sermon.id,
        new_cut(status="suggested"),
        new_cut(status="chosen"),
        new_cut(status="chosen"),
        new_cut(status="discarded"),
    )
    store(connection, other.id, new_cut(status="suggested"))

    assert cuts.counts_of(connection, sermon.id) == {"suggested": 1, "chosen": 2, "discarded": 1}


def test_deleting_the_cuts_of_one_sermon_keeps_the_other_sermons_ones(
    connection: sqlite3.Connection,
) -> None:
    replaced = sermons.insert(connection, new_sermon("Aaaaaaaaaa1"))
    kept = sermons.insert(connection, new_sermon("Aaaaaaaaaa2"))
    store(connection, replaced.id, new_cut())
    store(connection, kept.id, new_cut("Mantido"))

    with connection:
        cuts.delete_of(connection, replaced.id)

    assert (
        cuts.of_sermon(connection, replaced.id),
        [cut.title for cut in cuts.of_sermon(connection, kept.id)],
    ) == ([], ["Mantido"])


def test_deleting_the_unedited_suggestions_keeps_edited_chosen_discarded_and_other_sermons(
    connection: sqlite3.Connection,
) -> None:
    sermon = sermons.insert(connection, new_sermon("Aaaaaaaaaa1"))
    other = sermons.insert(connection, new_sermon("Aaaaaaaaaa2"))
    store(
        connection,
        sermon.id,
        new_cut("Sugerido"),
        new_cut("Editado"),
        new_cut("Escolhido", status="chosen"),
        new_cut("Descartado", status="discarded"),
    )
    store(connection, other.id, new_cut("De outra pregação"))
    with connection:
        connection.execute("UPDATE cuts SET edited = 1 WHERE title = 'Editado'")
    kept = [cut for cut in cuts.of_sermon(connection, sermon.id) if cut.title != "Sugerido"]
    elsewhere = cuts.of_sermon(connection, other.id)

    with connection:
        cuts.delete_unedited_suggestions(connection, sermon.id)

    assert (cuts.of_sermon(connection, sermon.id), cuts.of_sermon(connection, other.id)) == (
        kept,
        elsewhere,
    )


def test_deleting_a_sermon_deletes_its_cuts(connection: sqlite3.Connection) -> None:
    sermon = sermons.insert(connection, new_sermon())
    store(connection, sermon.id, new_cut())

    with connection:
        connection.execute("DELETE FROM sermons WHERE id = ?", (sermon.id,))

    assert connection.execute("SELECT COUNT(*) FROM cuts").fetchone() == (0,)


def test_deleting_the_preset_of_old_cuts_keeps_them_without_their_preset(
    connection: sqlite3.Connection,
) -> None:
    sermon = sermons.insert(connection, new_sermon())
    old = create_preset(connection, "Antigo")
    store(connection, sermon.id, new_cut(preset_id=old["id"]))

    delete_preset(connection, old["id"])

    assert [cut.preset_id for cut in cuts.of_sermon(connection, sermon.id)] == [None]


@pytest.mark.parametrize(
    "unknown", [{"status": "published"}, {"source": "user"}], ids=["status", "source"]
)
def test_a_cut_outside_the_known_states_and_sources_is_refused(
    connection: sqlite3.Connection, unknown: dict[str, Any]
) -> None:
    sermon = sermons.insert(connection, new_sermon())

    with pytest.raises(sqlite3.IntegrityError):
        store(connection, sermon.id, replace(new_cut(), **unknown))


def migrations_up_to(tmp_path: Path, last: int) -> Path:
    folder = tmp_path / "migrations"
    folder.mkdir()
    for packaged in MIGRATIONS.glob("*.sql"):
        if int(packaged.name.split("_")[0]) <= last:
            (folder / packaged.name).write_text(packaged.read_text(encoding="utf-8"))
    return folder


def test_a_database_at_schema_6_keeps_its_data_and_gains_no_cuts_nor_suggestion_error(
    tmp_path: Path,
) -> None:
    home = Home(tmp_path / "home")
    with closing(connect(home, migrations_up_to(tmp_path, 6))) as old, old:
        sermon_id = old.execute(
            "INSERT INTO sermons (youtube_id, url, title, service_date, live_finished, status,"
            " created_at, updated_at) VALUES ('Ab3_x-9QzLk', 'https://youtu.be/Ab3_x-9QzLk',"
            " 'Culto', '2026-10-18', 1, 'processed', '2026-10-26T22:40:00+00:00',"
            " '2026-10-26T22:40:00+00:00')"
        ).lastrowid
        assert sermon_id is not None
        transcripts.replace(old, sermon_id, (Word("Amém.", 0.3, 0.9),), ())
        preset_id = create_preset(old, "Antigo")["id"]

    with closing(connect(home)) as migrated:
        sermon = sermons.by_id(migrated, sermon_id)
        assert sermon is not None
        assert (
            migrated.execute("PRAGMA user_version").fetchone()[0],
            (sermon.title, sermon.status, sermon.suggestion_error),
            [word.text for word in transcripts.words_of(migrated, sermon.id)],
            presets.by_id(migrated, preset_id) is not None,
            cuts.of_sermon(migrated, sermon.id),
            migrated.execute(
                "SELECT suggestion_error_code, suggestion_error_message FROM sermons"
            ).fetchall(),
        ) == (7, ("Culto", "processed", None), ["Amém."], True, [], [(None, None)])
