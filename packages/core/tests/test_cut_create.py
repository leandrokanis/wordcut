import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from wordcut.db import connect, sermons, transcripts
from wordcut.db.sermons import NewSermon
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.processing.sentences import split_sentences
from wordcut.service.cuts import create_cut, list_cuts, show_cut
from wordcut.transcript import Word

NOW = datetime(2026, 10, 27, 3, 0, tzinfo=timezone.utc)
# The sermon starts 1000 s into the live and lasts 120 s (sermon time 0 to 120).
SERMON_START = 1000.0
SERMON_LENGTH = 120.0


def even_words(count: int = 12, offset: float = 0.0) -> list[Word]:
    """``count`` sentences of two words each; sentence ``k`` spans ``offset + 10k`` to
    ``offset + 10k + 8`` s and its words are at positions ``2k`` and ``2k + 1``."""
    spoken = []
    for k in range(count):
        at = offset + 10.0 * k
        spoken += [Word("Frase", at, at + 4), Word(f"{k}.", at + 4.5, at + 8)]
    return spoken


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def new_sermon(connection: sqlite3.Connection, spoken: list[Word]) -> int:
    """A sermon, not processed yet, whose transcript is ``spoken``."""
    sermon = sermons.insert(
        connection,
        NewSermon(
            youtube_id="Ab3_x-9QzLk",
            url="https://youtu.be/Ab3_x-9QzLk",
            title="Culto de domingo",
            service_date=date(2026, 10, 18),
            live_duration=7718.0,
            live_finished=True,
            created_at=NOW,
        ),
    )
    with connection:
        transcripts.replace(connection, sermon.id, spoken, split_sentences(spoken))
    return sermon.id


def processed_sermon(
    connection: sqlite3.Connection,
    spoken: list[Word] | None = None,
    length: float = SERMON_LENGTH,
) -> tuple[int, list[int]]:
    """A processed sermon ``length`` s long whose transcript is ``spoken`` (by default
    ``even_words``), and the IDs of its words in order."""
    sermon_id = new_sermon(connection, even_words() if spoken is None else spoken)
    with connection:
        sermons.record_processed(
            connection, sermon_id, SERMON_START, SERMON_START + length, "sermon.mp4", NOW
        )
    return sermon_id, [word.id for word in transcripts.words_of(connection, sermon_id)]


def test_a_created_cut_spans_the_snapped_range_plays_all_of_it_and_is_chosen_by_the_admin(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)

    answer = create_cut(connection, sermon_id, 17.0, 41.0, now=NOW)

    assert (
        answer == show_cut(connection, answer["id"]),
        (answer["range_start_word"], answer["range_end_word"]),
        answer["segments"],
        (answer["status"], answer["source"], answer["sermon_id"]),
    ) == (
        True,
        (word[4], word[7]),
        [
            {
                "from_word": word[4],
                "to_word": word[7],
                "start": 20.0,
                "end": 38.0,
                "text": "Frase 2. Frase 3.",
            }
        ],
        ("chosen", "admin", sermon_id),
    )


@pytest.mark.parametrize(
    ("offset", "start", "end", "title"),
    [
        (0.0, 17.0, 41.0, "Novo corte · 00:20"),
        (4503.0, 4500.0, 4530.0, "Novo corte · 75:03"),
    ],
    ids=["seconds padded", "minutes past the hour"],
)
def test_without_a_title_the_cut_is_named_after_where_its_snapped_range_starts(
    connection: sqlite3.Connection, offset: float, start: float, end: float, title: str
) -> None:
    sermon_id, _ = processed_sermon(connection, even_words(offset=offset), offset + SERMON_LENGTH)

    assert create_cut(connection, sermon_id, start, end, now=NOW)["title"] == title


@pytest.mark.parametrize(
    ("given", "title"),
    [("  Graça que alcança  ", "Graça que alcança"), ("   ", "Novo corte · 00:20")],
    ids=["given, trimmed", "blank is no title"],
)
def test_a_given_title_is_trimmed_and_a_blank_one_counts_as_none(
    connection: sqlite3.Connection, given: str, title: str
) -> None:
    sermon_id, _ = processed_sermon(connection)

    assert create_cut(connection, sermon_id, 17.0, 41.0, given, now=NOW)["title"] == title


RANGE_REFUSED: dict[str, tuple[float, float]] = {
    "end before the start": (40.0, 20.0),
    "end at the start": (30.0, 30.0),
    "a border that is not a number": (float("nan"), 40.0),
    "an infinite border": (0.0, float("inf")),
    "starting before the sermon": (-1.0, 40.0),
    "ending after the sermon": (100.0, SERMON_LENGTH + 1),
    "shorter than 10 s once snapped": (19.0, 31.0),
    "end snapping before the start": (26.0, 27.0),
}


@pytest.mark.parametrize("case", list(RANGE_REFUSED))
def test_a_range_that_breaks_a_rule_is_invalid_argument_and_creates_nothing(
    connection: sqlite3.Connection, case: str
) -> None:
    sermon_id, _ = processed_sermon(connection)

    with pytest.raises(WordcutError) as refused:
        create_cut(connection, sermon_id, *RANGE_REFUSED[case], now=NOW)

    assert (refused.value.code, refused.value.details, list_cuts(connection, sermon_id)) == (
        "invalid_argument",
        {"argument": "range"},
        {"items": []},
    )


def test_creating_a_cut_on_a_sermon_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(WordcutError) as refused:
        create_cut(connection, 999, 17.0, 41.0, now=NOW)

    assert refused.value.code == "not_found"


def test_creating_a_cut_on_a_sermon_not_processed_is_refused_and_creates_nothing(
    connection: sqlite3.Connection,
) -> None:
    sermon_id = new_sermon(connection, even_words())

    with pytest.raises(WordcutError) as refused:
        create_cut(connection, sermon_id, 17.0, 41.0, now=NOW)

    assert (refused.value.code, list_cuts(connection, sermon_id)) == (
        "sermon_not_processed",
        {"items": []},
    )


def test_a_range_from_just_before_a_sentence_starts_at_that_sentence(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)

    answer = create_cut(connection, sermon_id, 29.0, 89.0, now=NOW)

    assert (answer["range_start_word"], answer["range_end_word"]) == (word[6], word[17])
