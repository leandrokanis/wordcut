import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from wordcut.db import MIGRATIONS, connect, sermons, transcripts
from wordcut.db.sermons import NewSermon
from wordcut.db.transcripts import SentenceRow, WordRow
from wordcut.home import Home
from wordcut.processing.sentences import Sentence
from wordcut.transcript import Word

CREATED_AT = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)


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
        created_at=CREATED_AT,
    )


def migrations_up_to(tmp_path: Path, last: int) -> Path:
    folder = tmp_path / "migrations"
    folder.mkdir()
    for packaged in MIGRATIONS.glob("*.sql"):
        if int(packaged.name.split("_")[0]) <= last:
            (folder / packaged.name).write_text(packaged.read_text(encoding="utf-8"))
    return folder


def test_a_database_at_schema_3_keeps_its_sermons_and_gains_empty_transcripts(
    tmp_path: Path,
) -> None:
    home = Home(tmp_path / "home")
    with closing(connect(home, migrations_up_to(tmp_path, 3))) as old, old:
        old.execute(
            "INSERT INTO sermons (youtube_id, url, title, service_date, live_finished, status,"
            " live_start, live_end, created_at, updated_at) VALUES ('Ab3_x-9QzLk',"
            " 'https://youtu.be/Ab3_x-9QzLk', 'Culto', '2026-10-18', 1, 'trimmed', 10, 900,"
            " '2026-10-26T22:40:00+00:00', '2026-10-26T22:40:00+00:00')"
        )

    with closing(connect(home)) as migrated:
        [kept] = sermons.newest_first(migrated)
        assert (
            migrated.execute("PRAGMA user_version").fetchone()[0] >= 4,
            (kept.title, kept.status, kept.live_start, kept.live_end),
            (kept.sermon_start, kept.sermon_end, kept.video_path, kept.processed_at),
            transcripts.words_of(migrated, kept.id),
            transcripts.sentences_of(migrated, kept.id),
        ) == (True, ("Culto", "trimmed", 10, 900), (None, None, None, None), [], [])


WORDS = (
    Word("Irmãos", 0.3, 0.7, score=0.91),
    Word("graça.", 0.8, 1.3, score=None, estimated=True),
    Word("Amém.", 98.8, 100.3, score=0.97),
)
SENTENCES = (
    Sentence(first_word=0, last_word=1, start=0.3, end=1.3, text="Irmãos graça."),
    Sentence(first_word=2, last_word=2, start=98.8, end=100.3, text="Amém."),
)


def record(connection: sqlite3.Connection, sermon_id: int) -> None:
    with connection:
        transcripts.replace(connection, sermon_id, WORDS, SENTENCES)


def test_recorded_words_and_sentences_are_read_back_in_order_pointing_to_their_words(
    connection: sqlite3.Connection,
) -> None:
    sermon = sermons.insert(connection, new_sermon())

    record(connection, sermon.id)

    words = transcripts.words_of(connection, sermon.id)
    ids = [word.id for word in words]
    assert (words, without_ids(transcripts.sentences_of(connection, sermon.id))) == (
        [
            WordRow(ids[0], 0, "Irmãos", 0.3, 0.7, 0.91, False),
            WordRow(ids[1], 1, "graça.", 0.8, 1.3, None, True),
            WordRow(ids[2], 2, "Amém.", 98.8, 100.3, 0.97, False),
        ],
        [
            (0, ids[0], ids[1], 0.3, 1.3, "Irmãos graça."),
            (1, ids[2], ids[2], 98.8, 100.3, "Amém."),
        ],
    )


def without_ids(sentences: list[SentenceRow]) -> list[tuple[object, ...]]:
    return [
        (row.position, row.first_word_id, row.last_word_id, row.start, row.end, row.text)
        for row in sentences
    ]


def test_replacing_one_sermons_transcript_keeps_the_other_sermons_one(
    connection: sqlite3.Connection,
) -> None:
    kept = sermons.insert(connection, new_sermon("Aaaaaaaaaa1"))
    replaced = sermons.insert(connection, new_sermon("Aaaaaaaaaa2"))
    record(connection, kept.id)
    before = (
        transcripts.words_of(connection, kept.id),
        transcripts.sentences_of(connection, kept.id),
    )

    record(connection, replaced.id)
    with connection:
        transcripts.delete_of(connection, replaced.id)

    assert (
        transcripts.words_of(connection, kept.id),
        transcripts.sentences_of(connection, kept.id),
        transcripts.words_of(connection, replaced.id),
    ) == (*before, [])


def test_rerecording_a_transcript_never_reuses_an_old_id(connection: sqlite3.Connection) -> None:
    sermon = sermons.insert(connection, new_sermon())
    record(connection, sermon.id)
    old_words = {word.id for word in transcripts.words_of(connection, sermon.id)}
    old_sentences = {row.id for row in transcripts.sentences_of(connection, sermon.id)}
    with connection:
        transcripts.delete_of(connection, sermon.id)

    record(connection, sermon.id)

    new_words = {word.id for word in transcripts.words_of(connection, sermon.id)}
    new_sentences = {row.id for row in transcripts.sentences_of(connection, sermon.id)}
    assert (old_words & new_words, old_sentences & new_sentences) == (set(), set())
