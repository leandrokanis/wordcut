"""The ``prepare`` task: thumbnails and waveform of a sermon's live, through doubles."""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut import timeline_media
from wordcut.db import MIGRATIONS, connect, sermons
from wordcut.db.sermons import NewSermon
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.processing import start_processing
from wordcut.service.sermons import (
    create_sermon,
    prepare_sermon_timeline,
    show_sermon,
    trim_sermon,
)
from wordcut.service.tasks import list_tasks
from wordcut.service.timeline import (
    timeline_thumbnails,
    timeline_thumbnails_layout,
    timeline_waveform,
)
from wordcut.timeline_media.storyboard import Storyboard
from wordcut.youtube import LiveInfo, YouTubeError

LINK = "https://youtu.be/Ab3_x-9QzLk"
CREATED_AT = datetime(2026, 10, 26, 19, 40, tzinfo=timezone(timedelta(hours=-3)))
PEAKS = [0.0, 0.5, 1.0]

FINISHED_LIVE = LiveInfo("Culto de domingo", date(2026, 10, 18), 7200.0, "was_live")

StartLockOwner = Callable[[str, str], "subprocess.Popen[str]"]


class FakeTimelineGateways:
    """``TimelineMediaGateways`` double; the audio failure carries what must not leak."""

    def __init__(self, *, storyboard: bool = True, audio_fails: bool = False) -> None:
        self._storyboard = storyboard
        self._audio_fails = audio_fails

    def storyboard(self, url: str, out_dir: Path) -> Storyboard | None:
        if not self._storyboard:
            return None
        out_dir.mkdir(parents=True, exist_ok=True)
        image = out_dir / "strip.jpg"
        image.write_bytes(b"jpeg")
        return Storyboard(image=image, width=160, height=90, times=[0.0, 3600.0])

    def audio(self, url: str, output: Path) -> Path:
        if self._audio_fails:
            raise YouTubeError("yt-dlp --cookies /segredos/youtube-cookies.txt: HTTP 403")
        output.write_bytes(b"audio")
        return output

    def peaks(self, audio: Path, buckets: int) -> list[float]:
        return PEAKS


@pytest.fixture
def home(wordcut_home: Path) -> Home:
    return Home(wordcut_home)


@pytest.fixture
def connection(home: Home) -> Iterator[sqlite3.Connection]:
    with closing(connect(home)) as opened:
        yield opened


class FakeLive:
    def info(self, url: str) -> LiveInfo:
        return FINISHED_LIVE


def use_gateways(monkeypatch: pytest.MonkeyPatch, gateways: FakeTimelineGateways) -> None:
    monkeypatch.setattr(timeline_media, "default_gateways", lambda: gateways)


def new_sermon(connection: sqlite3.Connection) -> int:
    """A sermon recorded as it is, with no preparation launched."""
    row = sermons.insert(
        connection,
        NewSermon(
            youtube_id="Ab3_x-9QzLk",
            url=LINK,
            title="Culto de domingo",
            service_date=date(2026, 10, 18),
            live_duration=7200.0,
            live_finished=True,
            created_at=CREATED_AT,
        ),
    )
    return row.id


def timeline_of(connection: sqlite3.Connection, home: Home, sermon_id: int) -> Any:
    return show_sermon(connection, sermon_id, home=home)["timeline"]


def test_preparation_makes_the_timeline_ready_with_its_thumbnails_and_waveform(
    home: Home, connection: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_gateways(monkeypatch, FakeTimelineGateways())
    sermon_id = new_sermon(connection)

    prepare_sermon_timeline(home, sermon_id, detach=False)

    assert timeline_of(connection, home, sermon_id) == {
        "status": "ready",
        "error": None,
        "task_id": None,
    }
    assert timeline_waveform(connection, home, sermon_id) == {"buckets": 3, "peaks": PEAKS}
    assert timeline_thumbnails_layout(connection, home, sermon_id) == {
        "width": 160,
        "height": 90,
        "times": [0.0, 3600.0],
    }


def test_audio_that_fails_leaves_the_timeline_failed_with_a_generic_message(
    home: Home, connection: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_gateways(monkeypatch, FakeTimelineGateways(audio_fails=True))
    sermon_id = new_sermon(connection)

    with pytest.raises(WordcutError) as raised:
        prepare_sermon_timeline(home, sermon_id, detach=False)

    timeline = timeline_of(connection, home, sermon_id)
    told = f"{raised.value.message} {timeline['error']['message']}"
    assert (timeline["status"], timeline["error"]["code"], raised.value.code) == (
        "failed",
        "youtube_error",
        "youtube_error",
    )
    assert not any(leak in told for leak in ("yt-dlp", "cookies", "/segredos", "403"))


def test_live_without_storyboard_is_ready_with_only_the_waveform(
    home: Home, connection: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = new_sermon(connection)
    use_gateways(monkeypatch, FakeTimelineGateways())
    prepare_sermon_timeline(home, sermon_id, detach=False)
    use_gateways(monkeypatch, FakeTimelineGateways(storyboard=False))

    prepare_sermon_timeline(home, sermon_id, detach=False)

    with pytest.raises(WordcutError) as raised:
        timeline_thumbnails(connection, home, sermon_id)
    assert (timeline_of(connection, home, sermon_id)["status"], raised.value.code) == (
        "ready",
        "not_found",
    )
    assert timeline_waveform(connection, home, sermon_id)["peaks"] == PEAKS


def test_preparation_runs_while_the_processing_lock_is_held(
    home: Home,
    connection: sqlite3.Connection,
    monkeypatch: pytest.MonkeyPatch,
    lock_owner: StartLockOwner,
) -> None:
    use_gateways(monkeypatch, FakeTimelineGateways())
    sermon_id = new_sermon(connection)
    lock_owner("process", "sermon 99")

    prepare_sermon_timeline(home, sermon_id, detach=False)

    assert timeline_of(connection, home, sermon_id)["status"] == "ready"


def test_a_second_preparation_while_one_runs_is_busy_naming_the_running_task(
    home: Home, connection: sqlite3.Connection, harmless_tasks: list[Any]
) -> None:
    sermon_id = new_sermon(connection)
    running = prepare_sermon_timeline(home, sermon_id, detach=True)

    with pytest.raises(WordcutError) as raised:
        prepare_sermon_timeline(home, sermon_id, detach=True)

    assert (
        raised.value.code,
        (raised.value.details or {}).get("task_id"),
        len(harmless_tasks),
    ) == (
        "busy",
        running.id,
        1,
    )


def test_preparing_a_ready_timeline_again_redoes_it(
    home: Home, connection: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_gateways(monkeypatch, FakeTimelineGateways())
    sermon_id = new_sermon(connection)
    first = prepare_sermon_timeline(home, sermon_id, detach=False)

    again = prepare_sermon_timeline(home, sermon_id, detach=False)

    assert (again.id != first.id, again.status) == (True, "succeeded")


def create(connection: sqlite3.Connection, home: Home, url: str = LINK) -> dict[str, Any]:
    return create_sermon(connection, FakeLive(), url, home=home)


def preparations(home: Home) -> list[dict[str, Any]]:
    return list_tasks(home, kind="prepare")["items"]


def test_creating_a_sermon_launches_the_preparation_of_its_timeline(
    home: Home, connection: sqlite3.Connection, harmless_tasks: list[Any]
) -> None:
    sermon_id = create(connection, home)["id"]

    [task] = preparations(home)
    assert (task["status"], task["sermon_id"], len(harmless_tasks)) == ("running", sermon_id, 1)
    assert timeline_of(connection, home, sermon_id) == {
        "status": "pending",
        "error": None,
        "task_id": task["id"],
    }


def test_neither_creating_the_same_video_again_nor_showing_prepares_again(
    home: Home, connection: sqlite3.Connection, harmless_tasks: list[Any]
) -> None:
    sermon_id = create(connection, home)["id"]
    harmless_tasks[0].kill()
    harmless_tasks[0].wait()

    create(connection, home, f"{LINK}?si=abc")
    show_sermon(connection, sermon_id, home=home)

    assert len(preparations(home)) == 1


def test_a_sermon_from_before_the_timeline_media_migration_is_shown_not_prepared(
    home: Home, tmp_path: Path
) -> None:
    older = tmp_path / "migrations-0011"
    older.mkdir()
    for script in sorted(MIGRATIONS.glob("*.sql"))[:11]:
        shutil.copy(script, older)
    with closing(connect(home, older)) as connection:
        sermon_id = new_sermon(connection)

    with closing(connect(home)) as connection:
        timeline = timeline_of(connection, home, sermon_id)

    assert (timeline["status"], timeline["error"]["code"], timeline["task_id"]) == (
        "failed",
        "interrupted",
        None,
    )


def test_a_preparation_whose_process_died_is_shown_failed(
    home: Home, connection: sqlite3.Connection, harmless_tasks: list[Any]
) -> None:
    sermon_id = create(connection, home)["id"]
    harmless_tasks[0].kill()
    harmless_tasks[0].wait()

    timeline = timeline_of(connection, home, sermon_id)

    assert (timeline["status"], timeline["error"]["code"]) == ("failed", "interrupted")


def test_a_failed_preparation_neither_stops_trimming_nor_processing(
    home: Home, connection: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_gateways(monkeypatch, FakeTimelineGateways(audio_fails=True))
    sermon_id = new_sermon(connection)
    with pytest.raises(WordcutError):
        prepare_sermon_timeline(home, sermon_id, detach=False)

    trim_sermon(connection, sermon_id, 1000.0, 1100.0)
    task = start_processing(home, sermon_id, live=FakeLive(), detach=True)

    assert (task.kind, task.status) == ("process", "running")


def test_preparation_leaves_no_scratch_files_behind(
    home: Home, connection: sqlite3.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_gateways(monkeypatch, FakeTimelineGateways())
    sermon_id = new_sermon(connection)

    prepare_sermon_timeline(home, sermon_id, detach=False)

    assert sorted(path.name for path in home.sermon_media(sermon_id).iterdir()) == ["timeline"]
