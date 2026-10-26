import sqlite3
import subprocess
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from wordcut.db import connect, sermons
from wordcut.db.sermons import NewSermon, SermonRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.sermons import SermonVideo, sermon_video

StartLockOwner = Callable[[str, str], subprocess.Popen[str]]

NOW = datetime(2026, 10, 26, 19, 40, tzinfo=timezone(timedelta(hours=-3)))
VIDEO_PATH = "media/sermons/1/sermon.mp4"
# Arbitrary, non-repeating bytes standing for the processed 16:9 video.
VIDEO = bytes(range(256)) * 2


@pytest.fixture
def home(wordcut_home: Path) -> Home:
    return Home(wordcut_home)


@pytest.fixture
def connection(home: Home) -> Iterator[sqlite3.Connection]:
    with closing(connect(home)) as opened:
        yield opened


def new_sermon(connection: sqlite3.Connection, title: str = "Culto de domingo") -> SermonRow:
    return sermons.insert(
        connection,
        NewSermon(
            youtube_id="Ab3_x-9QzLk",
            url="https://youtu.be/Ab3_x-9QzLk",
            title=title,
            service_date=date(2026, 10, 18),
            live_duration=7200.0,
            live_finished=True,
            created_at=NOW,
        ),
    )


def processed(connection: sqlite3.Connection, home: Home, row: SermonRow) -> SermonRow:
    """The sermon ``processed``, with its video written under the data folder."""
    video = home.root / VIDEO_PATH
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(VIDEO)
    with connection:
        sermons.record_processed(connection, row.id, 1000.0, 1100.0, VIDEO_PATH, NOW)
    found = sermons.by_id(connection, row.id)
    assert found is not None
    return found


def test_video_of_a_processed_sermon_is_its_file_with_the_readable_name(
    connection: sqlite3.Connection, home: Home
) -> None:
    row = processed(connection, home, new_sermon(connection))

    video = sermon_video(connection, home, row.id)

    assert video == SermonVideo(
        path=home.root / VIDEO_PATH, suggested_name="2026-10-18 - Culto de domingo.mp4"
    )


@pytest.mark.parametrize("status", ["created", "trimmed", "processing", "failed"])
def test_a_sermon_not_processed_has_no_video_to_download(
    connection: sqlite3.Connection, home: Home, status: str
) -> None:
    row = new_sermon(connection)
    with connection:
        sermons.set_status(connection, row.id, status, NOW)

    with pytest.raises(WordcutError) as refused:
        sermon_video(connection, home, row.id)

    assert (refused.value.code, refused.value.exit_code) == ("sermon_not_processed", 5)


def test_a_processed_sermon_whose_video_left_the_disk_is_an_internal_error_without_the_data_folder(
    connection: sqlite3.Connection, home: Home
) -> None:
    row = processed(connection, home, new_sermon(connection))
    (home.root / VIDEO_PATH).unlink()

    with pytest.raises(WordcutError) as failed:
        sermon_video(connection, home, row.id)

    assert failed.value.to_dict() == {
        "code": "internal_error",
        "message": f"Vídeo da pregação {row.id} não encontrado.",
        "details": {"sermon_id": row.id},
    }


def test_a_processed_sermon_without_a_video_path_is_the_same_internal_error(
    connection: sqlite3.Connection, home: Home
) -> None:
    row = processed(connection, home, new_sermon(connection))
    with connection:
        connection.execute("UPDATE sermons SET video_path = NULL WHERE id = ?", (row.id,))

    with pytest.raises(WordcutError) as failed:
        sermon_video(connection, home, row.id)

    assert failed.value.to_dict() == {
        "code": "internal_error",
        "message": f"Vídeo da pregação {row.id} não encontrado.",
        "details": {"sermon_id": row.id},
    }


def test_video_of_a_missing_sermon_is_not_found(connection: sqlite3.Connection, home: Home) -> None:
    with pytest.raises(WordcutError) as refused:
        sermon_video(connection, home, 999)

    assert (refused.value.code, refused.value.exit_code) == ("not_found", 3)


def test_characters_forbidden_in_file_names_are_left_out_of_the_readable_name(
    connection: sqlite3.Connection, home: Home
) -> None:
    row = processed(connection, home, new_sermon(connection, 'Culto: "fé" / <graça>? *|\\'))

    video = sermon_video(connection, home, row.id)

    assert video.suggested_name == "2026-10-18 - Culto fé graça.mp4"


def test_video_is_found_while_another_process_holds_the_processing_lock(
    connection: sqlite3.Connection, home: Home, lock_owner: StartLockOwner
) -> None:
    row = processed(connection, home, new_sermon(connection))
    lock_owner("render", "cut 34")

    video = sermon_video(connection, home, row.id)

    assert video.path.read_bytes() == VIDEO
