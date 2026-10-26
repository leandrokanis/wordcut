import sqlite3
import subprocess
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
from wordcut.service.rendering import show_render
from wordcut.service.renders import list_renders, render_video
from wordcut.transcript import Word

StartLockOwner = Callable[[str, str], subprocess.Popen[str]]

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
)
OPTIONS = {"fillers": "remove", "pauses": "short", "caption": True, "quality": "high"}
# Arbitrary, non-repeating bytes standing for an exported 9:16 video.
VIDEO = bytes(range(256)) * 4 + b"amen"


@pytest.fixture
def home(wordcut_home: Path) -> Home:
    return Home(wordcut_home)


@pytest.fixture
def connection(home: Home) -> Iterator[sqlite3.Connection]:
    with closing(connect(home)) as opened:
        yield opened


def stored_cut(connection: sqlite3.Connection, title: str = "Graça que alcança") -> int:
    """A cut of a sermon of 2026-10-18 titled "Culto de domingo", never processed."""
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
        transcripts.replace(connection, sermon.id, SPOKEN, ())
        word = [row.id for row in transcripts.words_of(connection, sermon.id)]
        new = NewCut("chosen", title, (Segment(word[0], word[3]),), word[0], word[3], "llm", None)
        [cut_id] = cuts.insert_many(connection, sermon.id, [new], NOW)
    return cut_id


def exported(
    connection: sqlite3.Connection,
    home: Home,
    cut_id: int,
    created_at: datetime = NOW,
    options: dict[str, Any] | None = None,
) -> int:
    """An export of the cut recorded as the ``render`` task does, its file holding ``VIDEO``."""
    with connection:
        render_id = renders.insert(
            connection, NewRender(cut_id, "", 31.5, options or OPTIONS, created_at)
        )
        file = home.cut_media(cut_id) / f"{render_id}.mp4"
        renders.set_path(connection, render_id, str(file.relative_to(home.root)))
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(VIDEO)
    return render_id


def ids(listed: dict[str, Any]) -> list[int]:
    return [item["id"] for item in listed["items"]]


def test_the_exports_of_a_cut_are_listed_the_most_recent_first(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection)
    older = exported(connection, home, cut_id, NOW)
    newer = exported(connection, home, cut_id, NOW + timedelta(minutes=5))

    listed = list_renders(connection, home, cut_id)

    assert ids(listed) == [newer, older]


def test_exports_recorded_in_the_same_second_are_listed_the_last_recorded_first(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection)
    first = exported(connection, home, cut_id, NOW)
    second = exported(connection, home, cut_id, NOW + timedelta(seconds=1))
    third = exported(connection, home, cut_id, NOW + timedelta(seconds=1))

    listed = list_renders(connection, home, cut_id)

    assert ids(listed) == [third, second, first]


def test_a_listed_export_is_given_as_render_show_gives_it_with_its_options_as_recorded(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection)
    render_id = exported(connection, home, cut_id, options={"pauses": "natural", "fade": False})

    [item] = list_renders(connection, home, cut_id)["items"]

    assert item == {
        "id": render_id,
        "cut_id": cut_id,
        "path": str(home.cut_media(cut_id) / f"{render_id}.mp4"),
        "duration": 31.5,
        "created_at": "2026-10-26T22:40:00+00:00",
        "options": {"pauses": "natural", "fade": False},
    }


def test_an_export_shown_from_a_relative_data_folder_has_an_absolute_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    relative = Home(Path("data"))
    with closing(connect(relative)) as connection:
        cut_id = stored_cut(connection)
        render_id = exported(connection, relative, cut_id)

        shown = show_render(connection, relative, render_id)

    assert shown["path"] == str(tmp_path / relative.cut_media(cut_id) / f"{render_id}.mp4")


def test_listing_the_exports_of_a_cut_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection, home: Home
) -> None:
    with pytest.raises(WordcutError) as raised:
        list_renders(connection, home, 999)

    assert (raised.value.code, raised.value.details) == ("not_found", {"cut_id": 999})


def test_a_cut_never_exported_lists_no_exports(connection: sqlite3.Connection, home: Home) -> None:
    listed = list_renders(connection, home, stored_cut(connection))

    assert listed == {"items": []}


def test_showing_an_export_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection, home: Home
) -> None:
    with pytest.raises(WordcutError) as raised:
        show_render(connection, home, 999)

    assert (raised.value.code, raised.value.details) == ("not_found", {"render_id": 999})


def test_the_video_of_an_export_is_its_file_named_after_the_service_date_and_the_cut_title(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection, title='Graça: que / alcança?"')
    render_id = exported(connection, home, cut_id)

    video = render_video(connection, home, render_id)

    assert (video.suggested_name, video.path.read_bytes()) == (
        "2026-10-18 - Graça que alcança.mp4",
        VIDEO,
    )


def test_the_video_of_an_export_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection, home: Home
) -> None:
    with pytest.raises(WordcutError) as raised:
        render_video(connection, home, 999)

    assert (raised.value.code, raised.value.details) == ("not_found", {"render_id": 999})


def test_an_export_whose_file_left_the_disk_has_no_video_and_says_so_without_the_data_folder(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection)
    render_id = exported(connection, home, cut_id)
    (home.cut_media(cut_id) / f"{render_id}.mp4").unlink()

    with pytest.raises(WordcutError) as raised:
        render_video(connection, home, render_id)

    error = raised.value
    assert (error.code, error.details, str(home.root) in error.message) == (
        "internal_error",
        {"render_id": render_id},
        False,
    )


def test_an_export_whose_file_left_the_disk_is_still_shown_from_its_record(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection)
    render_id = exported(connection, home, cut_id)
    (home.cut_media(cut_id) / f"{render_id}.mp4").unlink()

    shown = show_render(connection, home, render_id)

    assert shown["path"] == str(home.cut_media(cut_id) / f"{render_id}.mp4")


def test_listing_showing_and_locating_exports_work_while_another_process_holds_the_lock(
    connection: sqlite3.Connection, home: Home, lock_owner: StartLockOwner
) -> None:
    cut_id = stored_cut(connection)
    render_id = exported(connection, home, cut_id)
    lock_owner("render", "cut 99")

    answers = (
        ids(list_renders(connection, home, cut_id)),
        show_render(connection, home, render_id)["id"],
        render_video(connection, home, render_id).path.read_bytes(),
    )

    assert answers == ([render_id], render_id, VIDEO)
