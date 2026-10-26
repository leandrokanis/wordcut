import sqlite3
import unicodedata
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.cuts import fix_word, list_cuts, preview_cut, show_cut
from wordcut.transcript import Word

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
LATER = NOW + timedelta(minutes=5)
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("Jesús", 0.9, 1.2),
    Word("não", 1.25, 1.3),
    Word("falha.", 1.35, 1.9),
    Word("Deus", 2.5, 2.8),
    Word("governa.", 2.85, 3.4),
)


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def processed_sermon(
    connection: sqlite3.Connection, youtube_id: str = "Ab3_x-9QzLk"
) -> tuple[int, list[int]]:
    """A new sermon with the ``SPOKEN`` words, and the IDs of those words in order."""
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
        transcripts.replace(connection, sermon.id, SPOKEN, ())
    return sermon.id, [word.id for word in transcripts.words_of(connection, sermon.id)]


def stored_cut(connection: sqlite3.Connection, sermon_id: int, *segments: Segment) -> int:
    """A ``suggested`` cut playing ``segments``, over the range from its first to its last
    word, and its ID."""
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


def test_fixing_a_word_answers_the_word_as_cut_show_gives_it_with_its_cut(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))

    fixed = fix_word(connection, cut_id, word[1], "Jesus", LATER)

    assert fixed == {
        "cut_id": cut_id,
        "word_id": word[1],
        "text": "Jesús",
        "start": 0.9,
        "end": 1.2,
        "corrected": "Jesus",
    }


def test_a_fixed_word_shows_its_fix_in_cut_show_and_keeps_its_original_text(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))

    fix_word(connection, cut_id, word[1], "Jesus", LATER)

    assert [
        (shown["text"], shown["corrected"]) for shown in show_cut(connection, cut_id)["words"]
    ] == [
        ("Irmãos,", None),
        ("Jesús", "Jesus"),
        ("não", None),
        ("falha.", None),
    ]


def test_a_fix_that_changes_the_word_is_too_different_and_says_how_far_without_the_typed_text(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))

    with pytest.raises(WordcutError) as refused:
        fix_word(connection, cut_id, word[2], "sim", LATER)

    error = refused.value
    assert (error.code, error.details, "sim" in error.message) == (
        "spelling_too_different",
        {"distance": 3, "limit": 1, "original": "não"},
        False,
    )


def test_fixing_a_word_back_to_its_original_spelling_removes_the_fix(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))
    fix_word(connection, cut_id, word[1], "Jesus", NOW)

    # Typed decomposed, with spaces around: still the original word.
    undone = fix_word(
        connection, cut_id, word[1], f" {unicodedata.normalize('NFD', 'Jesús')} ", LATER
    )

    assert (undone["corrected"], show_cut(connection, cut_id)["words"][1]["corrected"]) == (
        None,
        None,
    )


@pytest.mark.parametrize("text", ["Jesus", "Jesús"])
def test_a_successful_fix_or_undo_marks_the_cut_edited_at_that_moment(
    connection: sqlite3.Connection, text: str
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))

    fix_word(connection, cut_id, word[1], text, LATER)

    row = cuts.by_id(connection, cut_id)
    assert row is not None
    assert (row.edited, row.updated_at) == (True, LATER)


@pytest.mark.parametrize("which", ["missing", "other sermon", "in range, between segments"])
def test_a_word_the_cut_does_not_play_is_an_invalid_word_id(
    connection: sqlite3.Connection, which: str
) -> None:
    sermon_id, word = processed_sermon(connection)
    _, other = processed_sermon(connection, youtube_id="Zz9_y-8PwKj")
    # The range covers words 0 to 3; the segments skip word 2.
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[1]), Segment(word[3], word[3]))
    word_id = {"missing": 999_999, "other sermon": other[1], "in range, between segments": word[2]}

    with pytest.raises(WordcutError) as refused:
        fix_word(connection, cut_id, word_id[which], "nao", LATER)

    assert (refused.value.code, refused.value.details) == (
        "invalid_argument",
        {"argument": "word_id"},
    )


@pytest.mark.parametrize("text", ["", "   ", "Jesus Cristo", "Je\tsus"])
def test_a_text_that_is_not_one_word_is_an_invalid_text_without_echoing_it(
    connection: sqlite3.Connection, text: str
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))

    with pytest.raises(WordcutError) as refused:
        fix_word(connection, cut_id, word[1], text, LATER)

    error = refused.value
    assert (error.code, error.details, text.strip() != "" and text in error.message) == (
        "invalid_argument",
        {"argument": "text"},
        False,
    )


def test_fixing_a_word_of_a_cut_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection,
) -> None:
    _, word = processed_sermon(connection)

    with pytest.raises(WordcutError) as refused:
        fix_word(connection, 999, word[1], "Jesus", LATER)

    assert (refused.value.code, refused.value.details) == ("not_found", {"cut_id": 999})


def test_a_new_fix_of_the_same_word_replaces_the_previous_one(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))
    fix_word(connection, cut_id, word[3], "falha!", NOW)

    fix_word(connection, cut_id, word[3], "falha", LATER)

    assert show_cut(connection, cut_id)["words"][3]["corrected"] == "falha"


def test_the_lock_compares_with_the_original_word_so_fixes_cannot_drift_step_by_step(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))
    fix_word(connection, cut_id, word[1], "Jesus", NOW)

    # One edit away from "Jesus", two away from the original "Jesús".
    with pytest.raises(WordcutError) as refused:
        fix_word(connection, cut_id, word[1], "Jesu", LATER)

    assert (refused.value.code, refused.value.details) == (
        "spelling_too_different",
        {"distance": 2, "limit": 1, "original": "Jesús"},
    )


@pytest.mark.parametrize(
    ("which", "text"),
    [("played", "sim"), ("played", "Jesus Cristo"), ("not played", "Jesus")],
)
def test_a_refused_fix_changes_nothing_in_the_cut(
    connection: sqlite3.Connection, which: str, text: str
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))
    fix_word(connection, cut_id, word[1], "Jesus", NOW)
    before = (show_cut(connection, cut_id), cuts.by_id(connection, cut_id))

    with pytest.raises(WordcutError):
        fix_word(connection, cut_id, word[1] if which == "played" else word[5], text, LATER)

    assert (show_cut(connection, cut_id), cuts.by_id(connection, cut_id)) == before


def test_a_fix_holds_only_in_its_cut(connection: sqlite3.Connection) -> None:
    sermon_id, word = processed_sermon(connection)
    fixed_cut = stored_cut(connection, sermon_id, Segment(word[0], word[3]))
    other_cut = stored_cut(connection, sermon_id, Segment(word[1], word[2]))

    fix_word(connection, fixed_cut, word[1], "Jesus", LATER)

    assert show_cut(connection, other_cut)["words"][0]["corrected"] is None


@pytest.mark.parametrize("view", ["cut show", "cut preview", "cut list"])
def test_two_cuts_fixing_the_same_word_each_keep_their_own_spelling(
    connection: sqlite3.Connection, view: str
) -> None:
    sermon_id, word = processed_sermon(connection)
    first_cut = stored_cut(connection, sermon_id, Segment(word[0], word[3]))
    second_cut = stored_cut(connection, sermon_id, Segment(word[1], word[2]))

    fix_word(connection, first_cut, word[1], "Jesus", LATER)
    fix_word(connection, second_cut, word[1], "JESUS", LATER)

    if view == "cut list":
        texts = [item["text"] for item in list_cuts(connection, sermon_id)["items"]]
    else:
        assemble = show_cut if view == "cut show" else preview_cut
        texts = [
            " ".join(segment["text"] for segment in assemble(connection, cut_id)["segments"])
            for cut_id in (first_cut, second_cut)
        ]
    assert texts == ["Irmãos, Jesus não falha.", "JESUS não"]


@pytest.mark.parametrize("view", ["cut show", "cut preview", "cut list"])
def test_undoing_a_fix_in_one_cut_keeps_the_fix_of_the_same_word_in_another_cut(
    connection: sqlite3.Connection, view: str
) -> None:
    sermon_id, word = processed_sermon(connection)
    kept_cut = stored_cut(connection, sermon_id, Segment(word[0], word[3]))
    undone_cut = stored_cut(connection, sermon_id, Segment(word[1], word[2]))
    fix_word(connection, kept_cut, word[1], "Jesus", LATER)
    fix_word(connection, undone_cut, word[1], "JESUS", LATER)

    fix_word(connection, undone_cut, word[1], "Jesús", LATER)

    if view == "cut list":
        texts = [item["text"] for item in list_cuts(connection, sermon_id)["items"]]
    else:
        assemble = show_cut if view == "cut show" else preview_cut
        texts = [
            " ".join(segment["text"] for segment in assemble(connection, cut_id)["segments"])
            for cut_id in (kept_cut, undone_cut)
        ]
    assert texts == ["Irmãos, Jesus não falha.", "Jesús não"]


def test_undoing_a_word_that_has_no_fix_succeeds_with_no_fix(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))

    assert fix_word(connection, cut_id, word[1], "Jesús", LATER)["corrected"] is None


@pytest.mark.parametrize(
    ("cut_exists", "word_played", "text", "code", "argument"),
    [
        (False, False, "dois termos", "not_found", None),
        (True, False, "dois termos", "invalid_argument", "word_id"),
        (True, True, "Jesús Jesús", "invalid_argument", "text"),
    ],
)
def test_refusals_come_in_order_cut_then_word_then_text_then_spelling(
    connection: sqlite3.Connection,
    cut_exists: bool,
    word_played: bool,
    text: str,
    code: str,
    argument: str | None,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3])) if cut_exists else 999

    with pytest.raises(WordcutError) as refused:
        fix_word(connection, cut_id, word[1] if word_played else word[5], text, LATER)

    shown = (refused.value.code, (refused.value.details or {}).get("argument"))
    assert shown == (code, argument)


@pytest.mark.parametrize(
    "removal",
    [
        "cut's sermon reprocessed",
        "sermon deleted",
        "unedited suggestions replaced",
        "transcript removed under the cut",
    ],
)
def test_removing_cuts_or_words_that_carry_fixes_takes_the_fixes_along(
    connection: sqlite3.Connection, removal: str
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[3]))
    fix_word(connection, cut_id, word[1], "Jesus", LATER)

    with connection:
        if removal == "cut's sermon reprocessed":
            cuts.delete_of(connection, sermon_id)
            transcripts.delete_of(connection, sermon_id)
        elif removal == "transcript removed under the cut":
            transcripts.delete_of(connection, sermon_id)
        elif removal == "sermon deleted":
            connection.execute("DELETE FROM sermons WHERE id = ?", (sermon_id,))
        else:
            cuts.delete_unedited_suggestions(connection, sermon_id)

    kept = cuts.by_id(connection, cut_id)
    assert (kept is None) == (removal in ("cut's sermon reprocessed", "sermon deleted"))


def test_cut_show_assembles_the_fixed_spelling_into_the_cut_and_segment_text(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[4], word[5]), Segment(word[0], word[1]))
    fix_word(connection, cut_id, word[1], "Jesus", LATER)

    shown = show_cut(connection, cut_id)

    assert (shown["text"], [segment["text"] for segment in shown["segments"]]) == (
        "Deus governa. Irmãos, Jesus",
        ["Deus governa.", "Irmãos, Jesus"],
    )


def test_preview_plays_the_fixed_spelling_with_the_same_times_order_and_duration(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[4], word[5]), Segment(word[0], word[1]))
    before = preview_cut(connection, cut_id)

    fix_word(connection, cut_id, word[1], "Jesus", LATER)

    assert preview_cut(connection, cut_id) == {
        **before,
        "segments": [
            before["segments"][0],
            {"start": 0.3, "end": 1.2, "text": "Irmãos, Jesus", "out_of_order": True},
        ],
    }


def test_cut_list_assembles_each_cut_with_its_own_fixes(connection: sqlite3.Connection) -> None:
    sermon_id, word = processed_sermon(connection)
    fixed_cut = stored_cut(connection, sermon_id, Segment(word[0], word[3]))
    stored_cut(connection, sermon_id, Segment(word[1], word[2]))
    fix_word(connection, fixed_cut, word[1], "Jesus", LATER)

    listed = list_cuts(connection, sermon_id)

    assert [item["text"] for item in listed["items"]] == [
        "Irmãos, Jesus não falha.",
        "Jesús não",
    ]


def test_a_word_the_cut_plays_twice_shows_its_fix_in_both_segments(
    connection: sqlite3.Connection,
) -> None:
    sermon_id, word = processed_sermon(connection)
    cut_id = stored_cut(connection, sermon_id, Segment(word[0], word[1]), Segment(word[1], word[2]))

    fix_word(connection, cut_id, word[1], "Jesus", LATER)

    shown = show_cut(connection, cut_id)
    assert (
        [segment["text"] for segment in shown["segments"]],
        [word["corrected"] for word in shown["words"]],
    ) == (["Irmãos, Jesus", "Jesus não"], [None, "Jesus", "Jesus", None])
