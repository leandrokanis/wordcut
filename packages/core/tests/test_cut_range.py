import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.edit.cut_range import shift_selection, snap_range, trim_segments
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.processing.sentences import Sentence, split_sentences
from wordcut.service.cuts import fix_word, list_cuts, move_range, set_range, show_cut
from wordcut.transcript import Word

NOW = datetime(2026, 10, 27, 3, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(minutes=5)


def even_words(count: int = 8) -> list[Word]:
    """``count`` sentences of two words each; sentence ``k`` spans ``10k`` to ``10k + 8`` s
    and its words are at positions ``2k`` and ``2k + 1``."""
    spoken = []
    for k in range(count):
        spoken += [
            Word("Frase", 10.0 * k, 10.0 * k + 4),
            Word(f"{k}.", 10.0 * k + 4.5, 10.0 * k + 8),
        ]
    return spoken


def even_sentences(count: int = 8) -> list[Sentence]:
    """The sentences of ``even_words``."""
    return split_sentences(even_words(count))


def test_the_start_snaps_to_the_nearest_sentence_start_and_the_end_to_the_nearest_end() -> None:
    assert snap_range(even_sentences(), 17.0, 41.0) == (4, 7)


def test_times_before_the_first_sentence_or_after_the_last_snap_to_the_sermon_borders() -> None:
    assert snap_range(even_sentences(), -5.0, 500.0) == (0, 15)


def test_trimming_cuts_the_segments_at_the_borders_and_drops_those_outside_in_play_order() -> None:
    segments = [(8, 10), (0, 2), (14, 15), (4, 5)]

    assert trim_segments(segments, (2, 9)) == [(8, 9), (2, 2), (4, 5)]


def test_moving_takes_each_chosen_sentence_to_the_one_starting_nearest_its_shifted_start() -> None:
    moved = shift_selection(even_sentences(), [(2, 3), (6, 7)], (10.0, 38.0), 20.0)

    assert moved == ((6, 11), [(6, 7), (10, 11)])


def test_moving_past_the_end_of_the_sermon_stops_at_it() -> None:
    moved = shift_selection(even_sentences(), [(2, 3), (6, 7)], (10.0, 38.0), 100.0)

    assert moved == ((10, 15), [(10, 11), (14, 15)])


def test_moving_past_the_start_of_the_sermon_stops_at_it() -> None:
    moved = shift_selection(even_sentences(), [(6, 7)], (20.0, 48.0), -100.0)

    assert moved == ((0, 5), [(2, 3)])


def test_a_sentence_chosen_only_in_part_goes_whole_to_its_destination() -> None:
    moved = shift_selection(even_sentences(), [(3, 3)], (10.0, 38.0), 10.0)

    assert moved == ((4, 9), [(4, 5)])


def uneven_sentences() -> list[Sentence]:
    """Six sentences of two words each, the fourth one long: 0–4, 5–9, 10–14, 15–40, 41–45
    and 46–50 s; sentence ``k`` has the words at positions ``2k`` and ``2k + 1``."""
    bounds = [(0.0, 4.0), (5.0, 9.0), (10.0, 14.0), (15.0, 40.0), (41.0, 45.0), (46.0, 50.0)]
    spoken = []
    for k, (start, end) in enumerate(bounds):
        middle = (start + end) / 2
        spoken += [Word("Frase", start, middle), Word(f"{k}.", middle, end)]
    return split_sentences(spoken)


def test_two_chosen_sentences_never_land_on_the_same_destination() -> None:
    moved = shift_selection(uneven_sentences(), [(2, 5)], (0.0, 40.0), 10.0)

    assert moved == ((4, 11), [(6, 7), (4, 5)])


def test_a_chosen_sentence_lands_only_on_a_sentence_of_the_new_range() -> None:
    moved = shift_selection(uneven_sentences(), [(4, 5)], (0.0, 14.0), 3.0)

    assert moved == ((2, 5), [(4, 5)])


def test_neighbouring_destinations_played_one_after_the_other_make_one_segment() -> None:
    moved = shift_selection(even_sentences(), [(2, 5)], (10.0, 38.0), 10.0)

    assert moved == ((4, 9), [(4, 7)])


def test_chosen_sentences_left_without_a_free_destination_are_left_out() -> None:
    moved = shift_selection(uneven_sentences(), [(0, 5)], (0.0, 14.0), 5.0)

    assert moved == ((2, 5), [(2, 5)])


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def processed_sermon(connection: sqlite3.Connection) -> tuple[int, list[int]]:
    """A new sermon whose transcript is ``even_words``, and the IDs of its words in order."""
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
    spoken = even_words()
    with connection:
        transcripts.replace(connection, sermon.id, spoken, split_sentences(spoken))
    return sermon.id, [word.id for word in transcripts.words_of(connection, sermon.id)]


def stored_cut(
    connection: sqlite3.Connection,
    sermon_id: int,
    segments: tuple[Segment, ...],
    range_words: tuple[int, int],
    status: str = "suggested",
) -> int:
    """A cut playing ``segments`` over the range of words ``range_words``."""
    with connection:
        [cut_id] = cuts.insert_many(
            connection,
            sermon_id,
            [NewCut(status, "Graça", segments, *range_words, "llm", None)],
            NOW,
        )
    return cut_id


def played(answer: dict[str, Any]) -> list[tuple[int, int]]:
    return [(segment["from_word"], segment["to_word"]) for segment in answer["segments"]]


def test_resizing_snaps_the_range_to_sentences_and_cuts_out_the_words_left_outside(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[1], word[7]),), (word[0], word[9]))

    answer = set_range(connection, cut_id, 17.0, 41.0, LATER)

    assert (
        answer,
        (answer["range_start_word"], answer["range_end_word"]),
        played(answer),
    ) == (show_cut(connection, cut_id), (word[4], word[7]), [(word[4], word[7])])


def test_a_border_not_given_stays_where_it_was(connection: sqlite3.Connection) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[1], word[7]),), (word[0], word[9]))

    moved_start = set_range(connection, cut_id, start=17.0, now=LATER)
    moved_end = set_range(connection, cut_id, end=39.0, now=LATER)

    assert [
        (answer["range_start_word"], answer["range_end_word"])
        for answer in (moved_start, moved_end)
    ] == [(word[4], word[9]), (word[4], word[7])]


def test_widening_offers_the_new_sentences_without_putting_them_in_the_cut(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[4], word[7]),), (word[4], word[7]))

    answer = set_range(connection, cut_id, 0.0, 48.0, LATER)

    assert (
        played(answer),
        [(sentence["first_word"], sentence["included"]) for sentence in answer["range_sentences"]],
    ) == (
        [(word[4], word[7])],
        [
            (word[0], "none"),
            (word[2], "none"),
            (word[4], "all"),
            (word[6], "all"),
            (word[8], "none"),
        ],
    )


def test_a_cut_whose_range_changed_is_edited_and_a_new_suggestion_keeps_it(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[1], word[7]),), (word[0], word[9]))

    set_range(connection, cut_id, 17.0, 41.0, LATER)
    with connection:
        cuts.delete_unedited_suggestions(connection, sermon_id)

    assert show_cut(connection, cut_id)["edited"] is True


RANGE_REFUSED: dict[str, dict[str, float]] = {
    "shorter than 10 s once snapped": {"start": 19.0, "end": 31.0},
    "end before the start": {"start": 40.0, "end": 20.0},
    "end at the start": {"start": 30.0, "end": 30.0},
    "end snapping before the start": {"start": 26.0, "end": 27.0},
    "no chosen sentence left inside": {"start": 40.0, "end": 78.0},
    "no border given": {},
    "a border that is not a number": {"start": float("nan"), "end": 40.0},
    "an infinite border": {"start": 0.0, "end": float("inf")},
}


@pytest.mark.parametrize("case", list(RANGE_REFUSED))
def test_a_range_that_breaks_a_rule_is_invalid_argument_and_changes_nothing(
    connection: sqlite3.Connection, case: str
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[1], word[7]),), (word[0], word[9]))
    before = cuts.by_id(connection, cut_id)

    with pytest.raises(WordcutError) as refused:
        set_range(connection, cut_id, **RANGE_REFUSED[case], now=LATER)

    assert (refused.value.code, refused.value.details, cuts.by_id(connection, cut_id)) == (
        "invalid_argument",
        {"argument": "range"},
        before,
    )


def test_the_words_that_stay_in_the_cut_keep_their_spelling_fixes(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[1], word[7]),), (word[0], word[9]))
    fix_word(connection, cut_id, word[4], "Frasse", NOW)

    answer = set_range(connection, cut_id, 17.0, 41.0, LATER)

    assert [shown["corrected"] for shown in answer["words"]] == ["Frasse", None, None, None]


def test_a_discarded_cut_can_still_have_its_range_changed_outside_the_web(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(
        connection, sermon_id, (Segment(word[1], word[7]),), (word[0], word[9]), "discarded"
    )

    answer = set_range(connection, cut_id, 17.0, 41.0, LATER)

    assert (answer["status"], played(answer)) == ("discarded", [(word[4], word[7])])


def test_changing_the_range_of_a_cut_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(WordcutError) as refused:
        set_range(connection, 99, 0.0, 20.0)

    assert (refused.value.code, refused.value.details) == ("not_found", {"cut_id": 99})


def test_moving_shifts_the_range_and_takes_the_chosen_sentences_along(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(
        connection,
        sermon_id,
        (Segment(word[6], word[7]), Segment(word[2], word[3])),
        (word[2], word[7]),
    )

    answer = move_range(connection, cut_id, 20.0, LATER)

    assert (
        answer,
        (answer["range_start_word"], answer["range_end_word"]),
        played(answer),
    ) == (
        show_cut(connection, cut_id),
        (word[6], word[11]),
        [(word[10], word[11]), (word[6], word[7])],
    )


def test_moving_a_cut_with_no_chosen_sentence_is_refused_as_an_empty_cut(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (), (word[2], word[7]))
    before = cuts.by_id(connection, cut_id)

    with pytest.raises(WordcutError) as refused:
        move_range(connection, cut_id, 20.0, LATER)

    assert (refused.value.code, refused.value.details, cuts.by_id(connection, cut_id)) == (
        "invalid_argument",
        {"argument": "range"},
        before,
    )


@pytest.mark.parametrize("by", [float("nan"), float("inf"), float("-inf")])
def test_moving_by_a_shift_that_is_not_a_number_of_seconds_is_invalid_argument(
    connection: sqlite3.Connection, by: float
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[2], word[3]),), (word[2], word[7]))
    before = cuts.by_id(connection, cut_id)

    with pytest.raises(WordcutError) as refused:
        move_range(connection, cut_id, by, LATER)

    assert (refused.value.code, refused.value.details, cuts.by_id(connection, cut_id)) == (
        "invalid_argument",
        {"argument": "by"},
        before,
    )


def test_a_listed_cut_gives_where_its_range_starts_and_ends_in_sermon_time(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    stored_cut(connection, sermon_id, (Segment(word[2], word[7]),), (word[0], word[9]))

    [listed] = list_cuts(connection, sermon_id)["items"]

    assert {key: listed[key] for key in ("start", "end", "range_start", "range_end")} == {
        "start": 10.0,
        "end": 38.0,
        "range_start": 0.0,
        "range_end": 48.0,
    }
