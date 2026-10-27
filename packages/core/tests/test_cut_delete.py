import os
import socket
import sqlite3
import subprocess
from collections.abc import Iterator
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, cast

import pytest

from wordcut.db import connect, cuts, renders, sermons, tasks, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.renders import NewRender
from wordcut.db.sermons import NewSermon
from wordcut.db.tasks import NewTask, TaskRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.cuts import delete_cut
from wordcut.transcript import Word

NOW = datetime(2026, 10, 27, 9, 30, tzinfo=timezone.utc)
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
)
# Arbitrary bytes standing for an exported 9:16 video.
VIDEO = b"exported cut"


@pytest.fixture
def home(wordcut_home: Path) -> Home:
    return Home(wordcut_home)


@pytest.fixture
def connection(home: Home) -> Iterator[sqlite3.Connection]:
    with closing(connect(home)) as opened:
        yield opened


def stored_sermon(connection: sqlite3.Connection) -> int:
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
    return sermon.id


def stored_cut(connection: sqlite3.Connection, sermon_id: int) -> int:
    word = [row.id for row in transcripts.words_of(connection, sermon_id)]
    new = NewCut("chosen", "Graça", (Segment(word[0], word[3]),), word[0], word[3], "llm", None)
    with connection:
        [cut_id] = cuts.insert_many(connection, sermon_id, [new], NOW)
    return cut_id


def exported(connection: sqlite3.Connection, home: Home, cut_id: int) -> Path:
    """An export of the cut recorded as the ``render`` task does, with its file on disk."""
    with connection:
        render_id = renders.insert(connection, NewRender(cut_id, "", 31.5, {}, NOW))
        file = home.cut_media(cut_id) / f"{render_id}.mp4"
        renders.set_path(connection, render_id, str(file.relative_to(home.root)))
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(VIDEO)
    return file


def running(
    connection: sqlite3.Connection, kind: str, resource_type: str, resource_id: int, pid: int
) -> TaskRow:
    """A task recorded ``running`` in the process ``pid`` of this host."""
    new = NewTask(kind, resource_type, resource_id, {}, pid, socket.gethostname(), NOW)
    return tasks.insert(connection, new)


def ended_process_pid() -> int:
    process = subprocess.Popen(["true"])
    process.wait()
    return process.pid


def recorded_at(connection: sqlite3.Connection, cut_id: int, path: str) -> None:
    """An export of the cut whose row names ``path``, relative to the data folder."""
    with connection:
        renders.insert(connection, NewRender(cut_id, path, 31.5, {}, NOW))


def test_a_deleted_cut_is_gone_with_its_exports_and_its_media_folder(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection, stored_sermon(connection))
    exported(connection, home, cut_id)
    (home.cut_media(cut_id) / "work").mkdir()

    delete_cut(home, connection, cut_id)

    assert (
        cuts.by_id(connection, cut_id),
        renders.of_cut(connection, cut_id),
        home.cut_media(cut_id).exists(),
    ) == (None, [], False)


def test_deleting_a_cut_leaves_the_other_cuts_of_the_sermon_and_their_files(
    connection: sqlite3.Connection, home: Home
) -> None:
    sermon_id = stored_sermon(connection)
    deleted, kept = stored_cut(connection, sermon_id), stored_cut(connection, sermon_id)
    exported(connection, home, deleted)
    kept_file = exported(connection, home, kept)

    delete_cut(home, connection, deleted)

    assert (
        cuts.by_id(connection, kept) is not None,
        len(renders.of_cut(connection, kept)),
        kept_file.read_bytes(),
    ) == (True, 1, VIDEO)


def test_a_cut_whose_export_file_is_already_gone_is_deleted_all_the_same(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection, stored_sermon(connection))
    exported(connection, home, cut_id).unlink()

    delete_cut(home, connection, cut_id)

    assert cuts.by_id(connection, cut_id) is None


def test_a_cut_that_does_not_exist_is_not_found(connection: sqlite3.Connection, home: Home) -> None:
    with pytest.raises(WordcutError) as raised:
        delete_cut(home, connection, 404)

    assert (raised.value.code, raised.value.details) == ("not_found", {"cut_id": 404})


def test_a_cut_being_exported_is_refused_as_busy_and_nothing_is_deleted(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection, stored_sermon(connection))
    file = exported(connection, home, cut_id)
    task = running(connection, "render", "cut", cut_id, os.getpid())

    with pytest.raises(WordcutError) as raised:
        delete_cut(home, connection, cut_id)

    assert (
        raised.value.code,
        raised.value.details,
        cuts.by_id(connection, cut_id) is not None,
        file.read_bytes(),
    ) == (
        "busy",
        {"task_id": task.id, "kind": "render", "started_at": NOW.isoformat()},
        True,
        VIDEO,
    )


def test_an_export_whose_process_is_gone_does_not_keep_the_cut_from_being_deleted(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection, stored_sermon(connection))
    running(connection, "render", "cut", cut_id, ended_process_pid())

    delete_cut(home, connection, cut_id)

    assert cuts.by_id(connection, cut_id) is None


@pytest.mark.parametrize("kind", ["process", "suggest"])
def test_a_cut_of_a_sermon_being_processed_or_suggested_is_refused_as_busy(
    connection: sqlite3.Connection, home: Home, kind: str
) -> None:
    sermon_id = stored_sermon(connection)
    cut_id = stored_cut(connection, sermon_id)
    task = running(connection, kind, "sermon", sermon_id, os.getpid())

    with pytest.raises(WordcutError) as raised:
        delete_cut(home, connection, cut_id)

    kept = cuts.by_id(connection, cut_id) is not None
    assert (raised.value.code, raised.value.details["task_id"], kept) == ("busy", task.id, True)


def test_the_export_tasks_of_a_deleted_cut_go_with_it_and_their_logs(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection, stored_sermon(connection))
    task = running(connection, "render", "cut", cut_id, ended_process_pid())
    home.task_log(task.id).parent.mkdir(parents=True, exist_ok=True)
    home.task_log(task.id).write_text("render\n")

    delete_cut(home, connection, cut_id)

    assert (tasks.by_id(connection, task.id), home.task_log(task.id).exists()) == (None, False)


def test_an_export_file_recorded_elsewhere_in_the_data_folder_is_deleted_too(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection, stored_sermon(connection))
    elsewhere = home.root / "media" / "older" / "7.mp4"
    elsewhere.parent.mkdir(parents=True)
    elsewhere.write_bytes(VIDEO)
    recorded_at(connection, cut_id, "media/older/7.mp4")

    delete_cut(home, connection, cut_id)

    assert not elsewhere.exists()


@pytest.mark.parametrize("named", ["../outside.mp4", "absolute"])
def test_an_export_path_outside_the_data_folder_is_never_deleted(
    connection: sqlite3.Connection, home: Home, tmp_path: Path, named: str
) -> None:
    cut_id = stored_cut(connection, stored_sermon(connection))
    bait = tmp_path / "outside.mp4"
    bait.write_bytes(VIDEO)
    recorded_at(connection, cut_id, str(bait) if named == "absolute" else named)

    delete_cut(home, connection, cut_id)

    assert (cuts.by_id(connection, cut_id), bait.read_bytes()) == (None, VIDEO)


class CommitFails:
    """A connection whose transactions never commit, as when the disk fails at the end."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    def __enter__(self) -> "CommitFails":
        return self

    def __exit__(self, *exc: object) -> None:
        self._connection.rollback()
        raise sqlite3.OperationalError("disk I/O error")


def test_a_delete_that_is_not_committed_leaves_the_files_on_disk(
    connection: sqlite3.Connection, home: Home
) -> None:
    cut_id = stored_cut(connection, stored_sermon(connection))
    file = exported(connection, home, cut_id)

    with pytest.raises(sqlite3.OperationalError):
        delete_cut(home, cast(sqlite3.Connection, CommitFails(connection)), cut_id)

    assert (cuts.by_id(connection, cut_id) is not None, file.read_bytes()) == (True, VIDEO)
