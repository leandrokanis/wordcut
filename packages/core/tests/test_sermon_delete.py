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

from wordcut.db import connect, cuts, renders, sermons, tasks, transcripts, word_fixes
from wordcut.db import timeline_media as timelines
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.renders import NewRender
from wordcut.db.sermons import NewSermon
from wordcut.db.tasks import NewTask, TaskRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.processing.sentences import Sentence
from wordcut.service.sermons import delete_sermon
from wordcut.transcript import Word

NOW = datetime(2026, 10, 27, 9, 30, tzinfo=timezone.utc)
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
)
SENTENCES = (Sentence(0, 3, 0.3, 1.9, "Irmãos, graça e paz."),)
# Arbitrary bytes standing for a video file.
VIDEO = b"video"


@pytest.fixture
def home(wordcut_home: Path) -> Home:
    return Home(wordcut_home)


@pytest.fixture
def connection(home: Home) -> Iterator[sqlite3.Connection]:
    with closing(connect(home)) as opened:
        yield opened


def written(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(VIDEO)
    return path


def stored_sermon(connection: sqlite3.Connection, youtube_id: str = "Ab3_x-9QzLk") -> int:
    """A sermon only created, with no media yet."""
    with connection:
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
    return sermon.id


def processed_sermon(
    connection: sqlite3.Connection, home: Home, youtube_id: str = "Ab3_x-9QzLk"
) -> int:
    """A processed sermon with its video, timeline and work folder, a transcript and two cuts,
    one with a spelling fix, each exported once."""
    sermon_id = stored_sermon(connection, youtube_id)
    media = home.sermon_media(sermon_id)
    written(media / "sermon.mp4")
    written(home.sermon_timeline(sermon_id) / "sheet-0.jpg")
    written(media / "work" / "audio.wav")
    timelines.record(connection, sermon_id, "ready", NOW)
    with connection:
        transcripts.replace(connection, sermon_id, SPOKEN, SENTENCES)
        video = str((media / "sermon.mp4").relative_to(home.root))
        sermons.record_processed(connection, sermon_id, 10.0, 12.0, video, NOW)
        word = [row.id for row in transcripts.words_of(connection, sermon_id)]
        new = NewCut("chosen", "Graça", (Segment(word[0], word[3]),), word[0], word[3], "llm", None)
        cut_ids = cuts.insert_many(connection, sermon_id, [new, new], NOW)
        word_fixes.put(connection, cut_ids[0], word[1], "Graça", NOW)
    for cut_id in cut_ids:
        exported(connection, home, cut_id)
    return sermon_id


def exported(connection: sqlite3.Connection, home: Home, cut_id: int) -> Path:
    with connection:
        render_id = renders.insert(connection, NewRender(cut_id, "", 31.5, {}, NOW))
        file = home.cut_media(cut_id) / f"{render_id}.mp4"
        renders.set_path(connection, render_id, str(file.relative_to(home.root)))
    return written(file)


def cut_ids_of(connection: sqlite3.Connection, sermon_id: int) -> list[int]:
    return [row.id for row in cuts.of_sermon(connection, sermon_id)]


def running(
    connection: sqlite3.Connection, kind: str, resource_type: str, resource_id: int, pid: int
) -> TaskRow:
    new = NewTask(kind, resource_type, resource_id, {}, pid, socket.gethostname(), NOW)
    return tasks.insert(connection, new)


def ended_process_pid() -> int:
    process = subprocess.Popen(["true"])
    process.wait()
    return process.pid


def rows_of(connection: sqlite3.Connection, sermon_id: int, cut_ids: list[int]) -> dict[str, int]:
    """How many rows of each table belong to the sermon or to the cuts ``cut_ids``."""
    marks = ",".join("?" * len(cut_ids)) or "NULL"
    by_sermon = ("sermons", "id"), ("cuts", "sermon_id"), ("words", "sermon_id")
    by_sermon += (("sentences", "sermon_id"), ("timeline_media", "sermon_id"))
    counts = {
        table: connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {column} = ?", (sermon_id,)
        ).fetchone()[0]
        for table, column in by_sermon
    }
    for table in ("renders", "word_fixes"):
        counts[table] = connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE cut_id IN ({marks})", cut_ids
        ).fetchone()[0]
    counts["tasks"] = connection.execute(
        "SELECT COUNT(*) FROM tasks WHERE (resource_type = 'sermon' AND resource_id = ?)"
        f" OR (resource_type = 'cut' AND resource_id IN ({marks}))",
        (sermon_id, *cut_ids),
    ).fetchone()[0]
    return counts


def test_a_deleted_sermon_is_gone_with_its_cuts_transcript_and_media_folder(
    connection: sqlite3.Connection, home: Home
) -> None:
    sermon_id = processed_sermon(connection, home)
    cut_ids = cut_ids_of(connection, sermon_id)

    delete_sermon(home, connection, sermon_id)

    assert (
        rows_of(connection, sermon_id, cut_ids),
        home.sermon_media(sermon_id).exists(),
        [home.cut_media(cut_id).exists() for cut_id in cut_ids],
    ) == (
        dict.fromkeys(("sermons", "cuts", "words", "sentences", "timeline_media", "renders"), 0)
        | {"word_fixes": 0, "tasks": 0},
        False,
        [False, False],
    )


@pytest.mark.parametrize("kind", ["process", "suggest", "prepare"])
def test_a_sermon_with_a_running_task_is_refused_as_busy_and_nothing_is_deleted(
    connection: sqlite3.Connection, home: Home, kind: str
) -> None:
    sermon_id = processed_sermon(connection, home)
    cut_ids = cut_ids_of(connection, sermon_id)
    before = rows_of(connection, sermon_id, cut_ids)
    task = running(connection, kind, "sermon", sermon_id, os.getpid())

    with pytest.raises(WordcutError) as raised:
        delete_sermon(home, connection, sermon_id)

    assert (
        raised.value.code,
        raised.value.details,
        rows_of(connection, sermon_id, cut_ids),
        home.sermon_media(sermon_id).exists(),
    ) == (
        "busy",
        {"task_id": task.id, "kind": kind, "started_at": NOW.isoformat()},
        before | {"tasks": 1},
        True,
    )


def test_a_sermon_with_one_of_its_cuts_being_exported_is_refused_as_busy(
    connection: sqlite3.Connection, home: Home
) -> None:
    sermon_id = processed_sermon(connection, home)
    task = running(connection, "render", "cut", cut_ids_of(connection, sermon_id)[1], os.getpid())

    with pytest.raises(WordcutError) as raised:
        delete_sermon(home, connection, sermon_id)

    kept = sermons.by_id(connection, sermon_id) is not None
    assert (raised.value.code, raised.value.details["task_id"], kept) == ("busy", task.id, True)


def test_the_tasks_of_the_sermon_and_of_its_cuts_go_with_it_and_their_logs(
    connection: sqlite3.Connection, home: Home
) -> None:
    sermon_id = processed_sermon(connection, home)
    cut_ids = cut_ids_of(connection, sermon_id)
    ended = [
        running(connection, "process", "sermon", sermon_id, ended_process_pid()),
        running(connection, "render", "cut", cut_ids[0], ended_process_pid()),
    ]
    logs = [written(home.task_log(task.id)) for task in ended]

    delete_sermon(home, connection, sermon_id)

    assert (
        [tasks.by_id(connection, task.id) for task in ended],
        [log.exists() for log in logs],
    ) == ([None, None], [False, False])


def test_deleting_a_sermon_leaves_the_other_sermons_rows_and_folders(
    connection: sqlite3.Connection, home: Home
) -> None:
    deleted = processed_sermon(connection, home)
    kept = processed_sermon(connection, home, "Zz9_y-8QzLk")
    kept_cuts = cut_ids_of(connection, kept)
    before = rows_of(connection, kept, kept_cuts)

    delete_sermon(home, connection, deleted)

    assert (
        rows_of(connection, kept, kept_cuts),
        home.sermon_media(kept).is_dir(),
        [home.cut_media(cut_id).is_dir() for cut_id in kept_cuts],
    ) == (before, True, [True, True])


def test_a_sermon_that_does_not_exist_is_not_found(
    connection: sqlite3.Connection, home: Home
) -> None:
    with pytest.raises(WordcutError) as raised:
        delete_sermon(home, connection, 404)

    assert (raised.value.code, raised.value.details) == ("not_found", {"sermon_id": 404})


def test_a_sermon_only_created_without_media_is_deleted(
    connection: sqlite3.Connection, home: Home
) -> None:
    sermon_id = stored_sermon(connection)

    deleted = delete_sermon(home, connection, sermon_id)

    assert (deleted, sermons.by_id(connection, sermon_id)) == (
        {"id": sermon_id, "deleted": True},
        None,
    )


def test_a_sermon_whose_video_is_already_gone_is_deleted_all_the_same(
    connection: sqlite3.Connection, home: Home
) -> None:
    sermon_id = processed_sermon(connection, home)
    (home.sermon_media(sermon_id) / "sermon.mp4").unlink()

    delete_sermon(home, connection, sermon_id)

    assert sermons.by_id(connection, sermon_id) is None


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


def test_a_sermon_delete_that_is_not_committed_leaves_the_files_on_disk(
    connection: sqlite3.Connection, home: Home
) -> None:
    sermon_id = processed_sermon(connection, home)

    with pytest.raises(sqlite3.OperationalError):
        delete_sermon(home, cast(sqlite3.Connection, CommitFails(connection)), sermon_id)

    assert (
        sermons.by_id(connection, sermon_id) is not None,
        (home.sermon_media(sermon_id) / "sermon.mp4").read_bytes(),
    ) == (True, VIDEO)
