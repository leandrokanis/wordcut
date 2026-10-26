import sqlite3
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from wordcut.db import connect, cuts, renders, sermons
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.renders import NewRender, RenderRow
from wordcut.db.sermons import NewSermon
from wordcut.home import Home

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
OPTIONS = {"pauses": "short", "caption": True}


@pytest.fixture
def connection(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    with closing(connect(Home(tmp_path))) as opened:
        yield opened


def stored_cut(connection: sqlite3.Connection) -> int:
    with connection:
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
        new = NewCut("chosen", "Graça que alcança", (Segment(1, 9),), 1, 9, "llm", None)
        [cut_id] = cuts.insert_many(connection, sermon.id, [new], NOW)
    return cut_id


def test_a_recorded_export_is_listed_with_its_cut_path_duration_options_and_date(
    connection: sqlite3.Connection,
) -> None:
    cut_id = stored_cut(connection)

    with connection:
        render_id = renders.insert(
            connection, NewRender(cut_id, "media/cuts/1/1.mp4", 58.2, OPTIONS, NOW)
        )

    assert renders.of_cut(connection, cut_id) == [
        RenderRow(render_id, cut_id, "media/cuts/1/1.mp4", 58.2, OPTIONS, NOW)
    ]


def test_the_exports_go_with_their_cut(connection: sqlite3.Connection) -> None:
    cut_id = stored_cut(connection)
    with connection:
        renders.insert(connection, NewRender(cut_id, "media/cuts/1/1.mp4", 58.2, OPTIONS, NOW))

    with connection:
        connection.execute("DELETE FROM cuts WHERE id = ?", (cut_id,))

    assert renders.of_cut(connection, cut_id) == []


def test_an_export_s_path_can_be_changed_and_it_is_found_by_its_id(
    connection: sqlite3.Connection,
) -> None:
    cut_id = stored_cut(connection)
    with connection:
        render_id = renders.insert(
            connection, NewRender(cut_id, "media/cuts/1/rendering.mp4", 58.2, OPTIONS, NOW)
        )

    with connection:
        renders.set_path(connection, render_id, f"media/cuts/1/{render_id}.mp4")

    found = renders.by_id(connection, render_id)
    assert (found.path if found else None) == f"media/cuts/1/{render_id}.mp4"
