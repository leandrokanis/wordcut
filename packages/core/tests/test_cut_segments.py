import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, cuts, renders, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.renders import NewRender
from wordcut.db.sermons import NewSermon
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.processing.sentences import split_sentences
from wordcut.service.cuts import fix_word, set_segments, show_cut
from wordcut.transcript import Word

NOW = datetime(2026, 10, 27, 3, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(minutes=5)
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
    Word("Deus", 2.5, 2.8),
    Word("governa.", 2.85, 3.4),
    Word("Ele", 3.5, 3.7),
    Word("salva.", 3.75, 4.2),
    Word("Amém.", 4.5, 4.9),
)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def processed_sermon(
    connection: sqlite3.Connection, youtube_id: str = "Ab3_x-9QzLk"
) -> tuple[int, list[int]]:
    """A new sermon with the ``SPOKEN`` words split into four sentences, and the IDs of the
    words in order."""
    sermon = sermons.insert(
        connection,
        NewSermon(
            youtube_id=youtube_id,
            url=f"https://youtu.be/{youtube_id}",
            title="Culto de domingo",
            service_date=date(2026, 10, 18),
            live_duration=7718.0,
            live_finished=True,
            created_at=NOW,
        ),
    )
    with connection:
        transcripts.replace(connection, sermon.id, SPOKEN, split_sentences(SPOKEN))
    return sermon.id, [word.id for word in transcripts.words_of(connection, sermon.id)]


def stored_cut(
    connection: sqlite3.Connection,
    sermon_id: int,
    segments: tuple[Segment, ...],
    range_words: tuple[int, int],
) -> int:
    """A ``suggested`` cut playing ``segments`` over the range of words ``range_words``."""
    with connection:
        [cut_id] = cuts.insert_many(
            connection,
            sermon_id,
            [NewCut("suggested", "Graça", segments, *range_words, "llm", None)],
            NOW,
        )
    return cut_id


def test_the_shown_cut_gives_the_sentences_of_its_range_in_order_with_how_much_it_plays(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[4]),), (word[0], word[7]))

    shown = show_cut(connection, cut_id)["range_sentences"]

    assert [(sentence["text"], sentence["included"]) for sentence in shown] == [
        ("Irmãos, graça e paz.", "all"),
        ("Deus governa.", "part"),
        ("Ele salva.", "none"),
    ]


def test_a_sentence_crossing_the_border_of_the_range_is_cut_down_to_the_range(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[2], word[3]),), (word[2], word[5]))

    [crossing, *_] = show_cut(connection, cut_id)["range_sentences"]

    assert {key: crossing[key] for key in crossing if key != "id"} == {
        "start": 1.25,
        "end": 1.9,
        "text": "e paz.",
        "first_word": word[2],
        "last_word": word[3],
        "included": "all",
    }


def test_the_sentences_outside_the_range_are_left_out(connection: sqlite3.Connection) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[4], word[5]),), (word[4], word[7]))

    shown = show_cut(connection, cut_id)["range_sentences"]

    assert [sentence["text"] for sentence in shown] == ["Deus governa.", "Ele salva."]


def test_setting_the_segments_stores_them_in_the_order_given_and_gives_the_cut(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[5]),), (word[0], word[7]))
    wanted = [
        {"from_word": word[4], "to_word": word[5]},
        {"from_word": word[0], "to_word": word[3]},
    ]

    answered = set_segments(connection, cut_id, wanted, LATER)

    assert (
        answered,
        [{"from_word": s["from_word"], "to_word": s["to_word"]} for s in answered["segments"]],
    ) == (show_cut(connection, cut_id), wanted)


def test_a_cut_whose_segments_were_set_is_edited_and_a_new_suggestion_keeps_it(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[5]),), (word[0], word[7]))

    set_segments(connection, cut_id, [{"from_word": word[0], "to_word": word[3]}], LATER)
    with connection:
        cuts.delete_unedited_suggestions(connection, sermon_id)

    assert show_cut(connection, cut_id)["edited"] is True


def span(first: int, last: int) -> dict[str, Any]:
    return {"from_word": first, "to_word": last}


REFUSED: dict[str, Callable[[list[int], list[int]], list[Any]]] = {
    "empty": lambda word, other: [],
    "backwards": lambda word, other: [span(word[5], word[4])],
    "missing word": lambda word, other: [span(word[0], 99_999)],
    "word of another sermon": lambda word, other: [span(other[0], other[1])],
    "past the end of the range": lambda word, other: [span(word[7], word[8])],
    "before the start of the range": lambda word, other: [span(word[0], word[2])],
    "overlapping": lambda word, other: [span(word[2], word[5]), span(word[1], word[3])],
    "repeated": lambda word, other: [span(word[1], word[3]), span(word[1], word[3])],
    "without to_word": lambda word, other: [{"from_word": word[1]}],
    "text for a word": lambda word, other: [{"from_word": str(word[1]), "to_word": word[3]}],
    "true for a word": lambda word, other: [{"from_word": True, "to_word": word[3]}],
    "not a range": lambda word, other: [word[1]],
}


@pytest.mark.parametrize("case", list(REFUSED))
def test_segments_that_break_a_rule_are_invalid_argument_and_change_nothing(
    connection: sqlite3.Connection, case: str
) -> None:
    sermon_id, word = processed_sermon(connection)
    _, other = processed_sermon(connection, "Zz9_y-8PqRs")
    cut_id = stored_cut(connection, sermon_id, (Segment(word[1], word[3]),), (word[1], word[7]))
    before = cuts.by_id(connection, cut_id)

    with pytest.raises(WordcutError) as refused:
        set_segments(connection, cut_id, REFUSED[case](word, other), LATER)

    assert (refused.value.code, refused.value.details, cuts.by_id(connection, cut_id)) == (
        "invalid_argument",
        {"argument": "segments"},
        before,
    )


def test_segments_may_reach_both_borders_of_the_range(connection: sqlite3.Connection) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[2], word[3]),), (word[1], word[7]))

    answered = set_segments(connection, cut_id, [span(word[6], word[7]), span(word[1], word[1])])

    assert answered["text"] == "Ele salva. graça"


def test_setting_the_segments_of_a_cut_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection,
) -> None:
    with pytest.raises(WordcutError) as refused:
        set_segments(connection, 99, [span(1, 2)])

    assert (refused.value.code, refused.value.details) == ("not_found", {"cut_id": 99})


def test_the_words_that_stay_in_the_cut_keep_their_spelling_fixes(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[5]),), (word[0], word[7]))
    fix_word(connection, cut_id, word[4], "Déus", NOW)

    answered = set_segments(connection, cut_id, [span(word[4], word[5])], LATER)

    assert [shown["corrected"] for shown in answered["words"]] == ["Déus", None]


def test_setting_the_segments_leaves_the_exports_already_made_as_they_were(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, (Segment(word[0], word[5]),), (word[0], word[7]))
    with connection:
        renders.insert(connection, NewRender(cut_id, "cuts/1/1.mp4", 31.5, {"fade": True}, NOW))
    before = show_cut(connection, cut_id)["renders"]

    answered = set_segments(connection, cut_id, [span(word[4], word[5])], LATER)

    assert answered["renders"] == before
