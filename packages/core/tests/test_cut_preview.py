import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.cuts import preview_cut, show_cut
from wordcut.transcript import Word

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
# Sermon time of each word; "e" starts exactly where "graça" ends.
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.2, 1.3),
    Word("paz.", 1.35, 1.9),
    Word("Deus", 2.5, 2.8),
    Word("governa.", 2.85, 3.4),
)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def processed_sermon(connection: sqlite3.Connection) -> tuple[int, list[int]]:
    """A sermon with the ``SPOKEN`` words, and the IDs of those words in order."""
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
        transcripts.replace(connection, sermon.id, SPOKEN, ())
    return sermon.id, [word.id for word in transcripts.words_of(connection, sermon.id)]


def stored_cut(
    connection: sqlite3.Connection, sermon_id: int, segments: tuple[Segment, ...]
) -> int:
    first = min(segment.from_word for segment in segments)
    last = max(segment.to_word for segment in segments)
    with connection:
        [cut_id] = cuts.insert_many(
            connection,
            sermon_id,
            [NewCut("suggested", "Graça que alcança", segments, first, last, "llm", None)],
            NOW,
        )
    return cut_id


def test_preview_plays_the_segments_in_cut_order_and_marks_the_one_that_goes_back_in_time(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    # A late, then B early (goes back in time), then C after B but still before A.
    cut_id = stored_cut(
        connection,
        sermon_id,
        (Segment(word[4], word[5]), Segment(word[0], word[1]), Segment(word[3], word[3])),
    )

    preview = preview_cut(connection, cut_id)

    assert preview == {
        "cut_id": cut_id,
        "duration": 2.35,
        "segments": [
            {"start": 2.5, "end": 3.4, "text": "Deus governa.", "out_of_order": False},
            {"start": 0.3, "end": 1.2, "text": "Irmãos, graça", "out_of_order": True},
            {"start": 1.35, "end": 1.9, "text": "paz.", "out_of_order": False},
        ],
    }


def test_a_segment_that_starts_exactly_where_the_previous_one_ends_is_not_out_of_order(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(
        connection, sermon_id, (Segment(word[0], word[1]), Segment(word[2], word[3]))
    )

    preview = preview_cut(connection, cut_id)

    assert [segment["out_of_order"] for segment in preview["segments"]] == [False, False]


def test_preview_lasts_as_long_as_the_shown_cut(connection: sqlite3.Connection) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(
        connection, sermon_id, (Segment(word[4], word[5]), Segment(word[0], word[3]))
    )

    preview = preview_cut(connection, cut_id)

    assert preview["duration"] == show_cut(connection, cut_id)["duration"]


def test_preview_of_a_cut_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(WordcutError) as raised:
        preview_cut(connection, 999)

    assert (raised.value.code, raised.value.details) == ("not_found", {"cut_id": 999})
