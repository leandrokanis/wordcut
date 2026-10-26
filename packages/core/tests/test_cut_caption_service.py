import sqlite3
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import CutRow, NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.cuts import caption_of, reset_caption, show_cut, update_caption
from wordcut.transcript import Word

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
LATER = NOW + timedelta(minutes=5)
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
)
CHURCH_STYLE = {
    "enabled": True,
    "font": "Open Sans Bold",
    "size": 60,
    "color": "#FFD600",
    "position": "center",
    "offset": 50,
    "border": 3,
    "border_color": "#000000",
    "shadow": "soft",
}


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


@pytest.fixture
def cut_id(connection: sqlite3.Connection) -> int:
    """A new ``suggested`` cut of a processed sermon, playing all its words."""
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
        word = [row.id for row in transcripts.words_of(connection, sermon.id)]
        segments = (Segment(word[0], word[3]),)
        new = NewCut("suggested", "Graça que alcança", segments, word[0], word[3], "llm", None)
        [created] = cuts.insert_many(connection, sermon.id, [new], NOW)
    return created


def test_a_new_cut_has_the_church_style(connection: sqlite3.Connection, cut_id: int) -> None:
    assert caption_of(connection, cut_id) == CHURCH_STYLE


def test_a_change_alters_only_the_given_fields_over_the_current_style(
    connection: sqlite3.Connection, cut_id: int
) -> None:
    update_caption(connection, cut_id, {"size": 72, "shadow": "strong"}, NOW)

    changed = update_caption(connection, cut_id, {"color": "#ffffff"}, LATER)

    assert (changed, caption_of(connection, cut_id)) == (
        {**CHURCH_STYLE, "size": 72, "shadow": "strong", "color": "#FFFFFF"},
    ) * 2


def test_a_change_stores_the_whole_style_in_the_cut(
    connection: sqlite3.Connection, cut_id: int
) -> None:
    update_caption(connection, cut_id, {"size": 72}, LATER)

    assert stored(connection, cut_id).caption == {**CHURCH_STYLE, "size": 72}


def test_a_change_marks_the_cut_edited_at_that_moment(
    connection: sqlite3.Connection, cut_id: int
) -> None:
    update_caption(connection, cut_id, {"enabled": False}, LATER)

    row = stored(connection, cut_id)
    assert (row.edited, row.updated_at) == (True, LATER)


def stored(connection: sqlite3.Connection, cut_id: int) -> CutRow:
    row = cuts.by_id(connection, cut_id)
    assert row is not None
    return row


def test_resetting_brings_back_the_church_style_turned_on(
    connection: sqlite3.Connection, cut_id: int
) -> None:
    update_caption(connection, cut_id, {"enabled": False, "size": 90}, NOW)

    reset = reset_caption(connection, cut_id, LATER)

    assert (reset, caption_of(connection, cut_id)) == (CHURCH_STYLE, CHURCH_STYLE)


def test_resetting_stores_no_style_and_marks_the_cut_edited(
    connection: sqlite3.Connection, cut_id: int
) -> None:
    reset_caption(connection, cut_id, LATER)

    row = stored(connection, cut_id)
    assert (row.caption, row.edited, row.updated_at) == (None, True, LATER)


def test_the_shown_cut_carries_its_effective_style(
    connection: sqlite3.Connection, cut_id: int
) -> None:
    before = show_cut(connection, cut_id)["caption"]
    update_caption(connection, cut_id, {"position": "bottom"}, LATER)

    after = show_cut(connection, cut_id)["caption"]

    assert (before, after) == (CHURCH_STYLE, {**CHURCH_STYLE, "position": "bottom", "offset": 78})


def test_a_refused_change_stores_nothing(connection: sqlite3.Connection, cut_id: int) -> None:
    before = stored(connection, cut_id)

    with pytest.raises(WordcutError):
        update_caption(connection, cut_id, {"size": 72, "color": "FFF"}, LATER)

    assert stored(connection, cut_id) == before


def test_an_incomplete_stored_style_is_completed_by_the_default(
    connection: sqlite3.Connection, cut_id: int
) -> None:
    with connection:
        cuts.set_caption(connection, cut_id, {"size": 90, "font_size": 72}, NOW)

    assert caption_of(connection, cut_id) == {**CHURCH_STYLE, "size": 90}


@pytest.mark.parametrize(
    "act",
    [
        lambda connection: caption_of(connection, 999),
        lambda connection: update_caption(connection, 999, {"size": 72}, LATER),
        lambda connection: reset_caption(connection, 999, LATER),
    ],
    ids=["show", "change", "reset"],
)
def test_the_style_of_a_cut_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection, act: Callable[[sqlite3.Connection], object]
) -> None:
    with pytest.raises(WordcutError) as raised:
        act(connection)

    assert (raised.value.code, raised.value.details) == ("not_found", {"cut_id": 999})


def test_turning_the_caption_off_and_on_changes_only_whether_it_shows(
    connection: sqlite3.Connection, cut_id: int
) -> None:
    styled = update_caption(connection, cut_id, {"size": 72, "shadow": "none"}, NOW)

    off = update_caption(connection, cut_id, {"enabled": False}, LATER)
    on = update_caption(connection, cut_id, {"enabled": True}, LATER)

    assert (off, on) == ({**styled, "enabled": False}, styled)
