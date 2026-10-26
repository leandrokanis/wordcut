import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.cuts.caption import DEFAULT_CAPTION
from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.cuts import choose_cut, discard_cut, list_cuts, restore_cut, show_cut
from wordcut.transcript import Word

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
# Sermon time of each word; the gaps between them are pauses the cut keeps.
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
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
    connection: sqlite3.Connection,
    sermon_id: int,
    segments: tuple[Segment, ...],
    *,
    title: str = "Graça que alcança",
    status: str = "suggested",
) -> int:
    first = min(segment.from_word for segment in segments)
    last = max(segment.to_word for segment in segments)
    with connection:
        [cut_id] = cuts.insert_many(
            connection,
            sermon_id,
            [NewCut(status, title, segments, first, last, "llm", None)],
            NOW,
        )
    return cut_id


def test_cut_text_joins_its_segments_in_the_order_it_plays_and_duration_adds_their_spans(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(
        connection, sermon_id, (Segment(word[4], word[5]), Segment(word[1], word[3]))
    )

    shown = show_cut(connection, cut_id)

    assert (shown["text"], shown["duration"]) == ("Deus governa. graça e paz.", 1.9)


def test_cut_segments_carry_their_times_and_text_and_its_words_follow_the_segments(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(
        connection, sermon_id, (Segment(word[4], word[5]), Segment(word[0], word[1]))
    )

    shown = show_cut(connection, cut_id)

    assert (shown["segments"], shown["words"]) == (
        [
            {"from_word": word[4], "to_word": word[5], "start": 2.5, "end": 3.4,
             "text": "Deus governa."},
            {"from_word": word[0], "to_word": word[1], "start": 0.3, "end": 1.2,
             "text": "Irmãos, graça"},
        ],
        [
            {"word_id": word[4], "text": "Deus", "start": 2.5, "end": 2.8, "corrected": None},
            {"word_id": word[5], "text": "governa.", "start": 2.85, "end": 3.4,
             "corrected": None},
            {"word_id": word[0], "text": "Irmãos,", "start": 0.3, "end": 0.8, "corrected": None},
            {"word_id": word[1], "text": "graça", "start": 0.9, "end": 1.2, "corrected": None},
        ],
    )  # fmt: skip


def test_shown_cut_has_the_sermon_cut_fields_plus_assembly_and_default_style_and_no_renders(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(
        connection, sermon_id, (Segment(word[4], word[4]), Segment(word[0], word[0]))
    )

    shown = show_cut(connection, cut_id)

    assert shown == {
        "id": cut_id,
        "sermon_id": sermon_id,
        "status": "suggested",
        "title": "Graça que alcança",
        "text": "Deus Irmãos,",
        "duration": 0.8,
        "segments": [
            {"from_word": word[4], "to_word": word[4], "start": 2.5, "end": 2.8, "text": "Deus"},
            {"from_word": word[0], "to_word": word[0], "start": 0.3, "end": 0.8,
             "text": "Irmãos,"},
        ],
        "range_start_word": word[0],
        "range_end_word": word[4],
        "source": "llm",
        "preset_id": None,
        "edited": False,
        "words": [
            {"word_id": word[4], "text": "Deus", "start": 2.5, "end": 2.8, "corrected": None},
            {"word_id": word[0], "text": "Irmãos,", "start": 0.3, "end": 0.8, "corrected": None},
        ],
        "caption": DEFAULT_CAPTION.as_dict(),
        "render_options": {},
        "renders": [],
    }  # fmt: skip


def test_shown_cut_keeps_the_caption_style_and_export_options_stored_with_it(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[3]),))
    with connection:
        connection.execute(
            "UPDATE cuts SET caption = ?, render_options = ? WHERE id = ?",
            ('{"font_size": 72}', '{"quality": "high"}', cut_id),
        )

    shown = show_cut(connection, cut_id)

    assert (shown["caption"], shown["render_options"]) == (
        DEFAULT_CAPTION.as_dict(),
        {"quality": "high"},
    )


def test_showing_a_cut_that_does_not_exist_is_not_found(connection: sqlite3.Connection) -> None:
    with pytest.raises(WordcutError) as raised:
        show_cut(connection, 999)

    assert raised.value.to_dict() == {
        "code": "not_found",
        "message": "Corte 999 não existe.",
        "details": {"cut_id": 999},
    }


def sermon_with_cuts_in(connection: sqlite3.Connection, *states: str) -> int:
    """A sermon with one cut in each of ``states``, added in that order and titled by it."""
    sermon_id, word = processed_sermon(connection)
    for number, status in enumerate(states, start=1):
        stored_cut(
            connection,
            sermon_id,
            (Segment(word[0], word[1]),),
            title=f"{number} {status}",
            status=status,
        )
    return sermon_id


def titles(listed: dict[str, Any]) -> list[str]:
    return [item["title"] for item in listed["items"]]


def test_cuts_are_listed_in_the_order_they_were_added_with_the_discarded_ones_last(
    connection: sqlite3.Connection,
) -> None:
    sermon_id = sermon_with_cuts_in(
        connection, "suggested", "discarded", "chosen", "suggested", "discarded"
    )

    listed = list_cuts(connection, sermon_id)

    assert titles(listed) == [
        "1 suggested",
        "3 chosen",
        "4 suggested",
        "2 discarded",
        "5 discarded",
    ]


def test_listed_cut_has_the_sermon_cut_fields_plus_its_text_and_duration_without_words(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[4], word[5]),), status="chosen")

    listed = list_cuts(connection, sermon_id)

    assert listed == {
        "items": [
            {
                "id": cut_id,
                "sermon_id": sermon_id,
                "status": "chosen",
                "title": "Graça que alcança",
                "text": "Deus governa.",
                "duration": 0.9,
                "segments": [{"from_word": word[4], "to_word": word[5]}],
                "range_start_word": word[4],
                "range_end_word": word[5],
                "source": "llm",
                "preset_id": None,
                "edited": False,
            }
        ]
    }


def test_listing_by_status_keeps_only_the_cuts_in_that_state(
    connection: sqlite3.Connection,
) -> None:
    sermon_id = sermon_with_cuts_in(connection, "chosen", "suggested", "discarded", "chosen")

    listed = list_cuts(connection, sermon_id, "chosen")

    assert titles(listed) == ["1 chosen", "4 chosen"]


def test_listing_the_cuts_of_a_sermon_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(WordcutError) as raised:
        list_cuts(connection, 999)

    assert raised.value.to_dict() == {
        "code": "not_found",
        "message": "Pregação 999 não existe.",
        "details": {"sermon_id": 999},
    }


def test_a_sermon_not_processed_yet_lists_no_cuts(connection: sqlite3.Connection) -> None:
    sermon_id = sermons.insert(
        connection,
        NewSermon(
            youtube_id="Zz9_y-8PqRs",
            url="https://youtu.be/Zz9_y-8PqRs",
            title="Culto de quarta",
            service_date=date(2026, 10, 21),
            live_duration=5400.0,
            live_finished=True,
            created_at=NOW,
        ),
    ).id

    assert list_cuts(connection, sermon_id) == {"items": []}


LATER = datetime(2026, 10, 27, 9, 15, tzinfo=timezone.utc)
Transition = Callable[[sqlite3.Connection, int, datetime], dict[str, Any]]


def test_choosing_a_suggested_cut_makes_it_chosen_and_gives_it_as_show_does(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[3]),))

    chosen = choose_cut(connection, cut_id, LATER)

    assert (chosen["status"], chosen) == ("chosen", show_cut(connection, cut_id))


def test_discarding_a_chosen_cut_makes_it_discarded(connection: sqlite3.Connection) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[3]),), status="chosen")

    discarded = discard_cut(connection, cut_id, LATER)

    assert (discarded["status"], show_cut(connection, cut_id)["status"]) == (
        "discarded",
        "discarded",
    )


def test_restoring_a_discarded_cut_makes_it_suggested_again(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[3]),), status="discarded")

    restored = restore_cut(connection, cut_id, LATER)

    assert (restored["status"], show_cut(connection, cut_id)["status"]) == (
        "suggested",
        "suggested",
    )


@pytest.mark.parametrize("status", ["suggested", "chosen"])
def test_restoring_a_cut_that_is_not_discarded_leaves_it_as_it_was(
    connection: sqlite3.Connection, status: str
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[3]),), status=status)
    before = cuts.by_id(connection, cut_id)

    restored = restore_cut(connection, cut_id, LATER)

    assert (restored["status"], cuts.by_id(connection, cut_id)) == (status, before)


@pytest.mark.parametrize(
    ("status", "transition"), [("chosen", choose_cut), ("discarded", discard_cut)]
)
def test_repeating_a_transition_writes_nothing(
    connection: sqlite3.Connection, status: str, transition: Transition
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[3]),), status=status)
    before = cuts.by_id(connection, cut_id)

    again = transition(connection, cut_id, LATER)

    assert (again["status"], cuts.by_id(connection, cut_id)) == (status, before)


def test_choosing_discarding_and_restoring_change_only_the_status_of_the_cut(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(
        connection, sermon_id, (Segment(word[4], word[5]), Segment(word[0], word[1]))
    )
    with connection:
        connection.execute(
            "UPDATE cuts SET caption = ?, render_options = ? WHERE id = ?",
            ('{"font_size": 72}', '{"quality": "high"}', cut_id),
        )
    before = cuts.by_id(connection, cut_id)
    assert before is not None

    choose_cut(connection, cut_id, LATER)
    discard_cut(connection, cut_id, LATER)
    restore_cut(connection, cut_id, LATER)

    assert cuts.by_id(connection, cut_id) == replace(before, updated_at=LATER)


@pytest.mark.parametrize("transition", [choose_cut, discard_cut, restore_cut])
def test_changing_the_state_of_a_cut_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection, transition: Transition
) -> None:
    with pytest.raises(WordcutError) as raised:
        transition(connection, 999, LATER)

    assert (raised.value.code, raised.value.details) == ("not_found", {"cut_id": 999})
