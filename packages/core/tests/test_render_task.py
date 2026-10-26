import sqlite3
import subprocess
from collections.abc import Callable, Sequence
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut import rendering
from wordcut.db import connect, cuts, renders, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.edit.timeline import Clip
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.cuts import caption_of, show_cut
from wordcut.service.rendering import estimate_render, show_render, start_render
from wordcut.service.tasks import list_tasks
from wordcut.tasks import BUILTIN_KIND_MODULES, kind
from wordcut.tasks import render as render_kind
from wordcut.transcript import Word
from wordcut.vertical.camera import CameraPath
from wordcut.vertical.captions import CaptionImage
from wordcut.vertical.detection import FrameDetections
from wordcut.vertical.render import Encoding

StartLockOwner = Callable[[str, str], subprocess.Popen[str]]

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
VIDEO_PATH = "media/sermons/1/sermon.mp4"
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
)
DEFAULT_SUMMARY = {
    "fillers": "remove",
    "stammers": "remove",
    "pauses": "natural",
    "smooth_joins": True,
    "fade": True,
    "normalize": True,
    "caption": True,
    "resolution": "1080x1920",
    "quality": "high",
}


class FakeGateways:
    """``RenderGateways`` double: the render writes a small file; nothing else is real."""

    def geometry(self, media: Path) -> tuple[int, int, float]:
        return 320, 180, 30.0

    def energy(self, media: Path) -> Callable[[float], float]:
        return lambda t: 0.0

    def assemble(
        self, source: Path, clips: Sequence[Clip], output: Path, fps: float, *, smooth_joins: bool
    ) -> Path:
        output.write_bytes(b"montage")
        return output

    def detect(self, montage: Path, progress: Callable[[int, int], None]) -> list[FrameDetections]:
        return [FrameDetections(False, ())] * 30

    def render(
        self,
        montage: Path,
        camera: CameraPath,
        captions: Sequence[CaptionImage],
        fps: float,
        output: Path,
        encoding: Encoding,
    ) -> Path:
        output.write_bytes(b"video")
        return output


@pytest.fixture
def home(wordcut_home: Path, monkeypatch: pytest.MonkeyPatch) -> Home:
    monkeypatch.setattr(rendering, "default_gateways", FakeGateways)
    return Home(wordcut_home)


def processed_cut(home: Home) -> int:
    """A chosen cut of a processed sermon whose video is in the data folder."""
    video = home.root / VIDEO_PATH
    video.parent.mkdir(parents=True, exist_ok=True)
    video.write_bytes(b"sermon")
    with closing(connect(home)) as connection, connection:
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
        sermons.record_processed(connection, sermon.id, 1000.0, 1100.0, VIDEO_PATH, NOW)
        word = [row.id for row in transcripts.words_of(connection, sermon.id)]
        new = NewCut("chosen", "Graça", (Segment(word[0], word[3]),), word[0], word[3], "llm", None)
        [cut_id] = cuts.insert_many(connection, sermon.id, [new], NOW)
    return cut_id


def rendered(home: Home, cut_id: int, **changes: Any) -> dict[str, Any]:
    task = start_render(home, cut_id, changes, detach=False)
    assert task.result is not None
    with closing(connect(home)) as connection:
        return show_render(connection, home, task.result["render_id"])


def test_render_is_a_builtin_kind_that_holds_the_processing_lock() -> None:
    assert ("wordcut.tasks.render" in BUILTIN_KIND_MODULES, kind("render").needs_lock) == (
        True,
        True,
    )


def test_an_export_in_the_foreground_is_recorded_with_its_file_named_after_it(
    home: Home,
) -> None:
    cut_id = processed_cut(home)

    export = rendered(home, cut_id)

    path = home.root / "media" / "cuts" / str(cut_id) / f"{export['id']}.mp4"
    assert (
        sorted(export),
        export["cut_id"],
        export["path"],
        Path(export["path"]).read_bytes(),
        export["options"],
    ) == (
        ["created_at", "cut_id", "duration", "id", "options", "path"],
        cut_id,
        str(path),
        b"video",
        DEFAULT_SUMMARY,
    )


def test_a_second_export_without_options_repeats_the_options_of_the_first(home: Home) -> None:
    cut_id = processed_cut(home)
    first = rendered(home, cut_id, pauses="short", fade=False, resolution="720x1280")

    second = rendered(home, cut_id)

    assert (second["options"], first["options"]["pauses"]) == (first["options"], "short")


def test_an_export_without_caption_turns_the_cut_s_caption_off_as_cut_caption_off_does(
    home: Home,
) -> None:
    cut_id = processed_cut(home)

    export = rendered(home, cut_id, caption=False)

    with closing(connect(home)) as connection:
        style, row = caption_of(connection, cut_id), cuts.by_id(connection, cut_id)
    assert (export["options"]["caption"], style["enabled"], row.edited if row else None) == (
        False,
        False,
        True,
    )


def test_with_the_machine_busy_the_export_is_refused_without_a_task_and_saves_nothing(
    home: Home, lock_owner: StartLockOwner
) -> None:
    cut_id = processed_cut(home)
    with closing(connect(home)) as connection:
        before = cuts.by_id(connection, cut_id)
    lock_owner("process", "sermon 1")

    with pytest.raises(WordcutError) as raised:
        start_render(home, cut_id, {"pauses": "short", "caption": False}, detach=False)

    with closing(connect(home)) as connection:
        after = cuts.by_id(connection, cut_id)
    assert (raised.value.code, list_tasks(home)["items"], after) == ("busy", [], before)


def test_a_cut_that_does_not_exist_is_not_found_even_with_the_machine_busy(
    home: Home, lock_owner: StartLockOwner
) -> None:
    lock_owner("process", "sermon 1")

    with pytest.raises(WordcutError) as raised:
        start_render(home, 999, {}, detach=False)

    assert (raised.value.code, raised.value.details) == ("not_found", {"cut_id": 999})


def test_a_cut_of_a_sermon_being_processed_again_is_refused_as_not_processed(
    home: Home, lock_owner: StartLockOwner
) -> None:
    cut_id = processed_cut(home)
    with closing(connect(home)) as connection, connection:
        row = cuts.by_id(connection, cut_id)
        assert row is not None
        sermons.set_status(connection, row.sermon_id, "processing", NOW)
    lock_owner("process", "sermon 1")

    with pytest.raises(WordcutError) as raised:
        start_render(home, cut_id, {}, detach=False)

    assert (raised.value.code, raised.value.exit_code) == ("sermon_not_processed", 5)


def test_an_invalid_option_is_refused_before_the_cut_is_looked_up(home: Home) -> None:
    with pytest.raises(WordcutError) as raised:
        start_render(home, 999, {"quality": "max"}, detach=False)

    assert (raised.value.code, raised.value.details) == (
        "invalid_argument",
        {"argument": "quality", "choices": ["high", "small"]},
    )


class FailingRender(FakeGateways):
    def render(
        self,
        montage: Path,
        camera: CameraPath,
        captions: Sequence[CaptionImage],
        fps: float,
        output: Path,
        encoding: Encoding,
    ) -> Path:
        output.write_bytes(b"part")
        raise RuntimeError("ffmpeg falhou")


def test_a_failed_export_fails_the_task_and_leaves_no_export_and_no_file(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rendering, "default_gateways", FailingRender)
    cut_id = processed_cut(home)

    with pytest.raises(WordcutError) as raised:
        start_render(home, cut_id, {}, detach=False)

    with closing(connect(home)) as connection:
        recorded = renders.of_cut(connection, cut_id)
    [task] = list_tasks(home)["items"]
    left = sorted(path.name for path in home.cut_media(cut_id).rglob("*"))
    assert (raised.value.code, task["status"], recorded, left) == (
        "internal_error",
        "failed",
        [],
        [],
    )


class InterruptedRender(FakeGateways):
    def render(
        self,
        montage: Path,
        camera: CameraPath,
        captions: Sequence[CaptionImage],
        fps: float,
        output: Path,
        encoding: Encoding,
    ) -> Path:
        output.write_bytes(b"part")
        raise KeyboardInterrupt


def test_an_interrupted_export_is_failed_as_interrupted_and_leaves_no_file(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rendering, "default_gateways", InterruptedRender)
    cut_id = processed_cut(home)

    with pytest.raises(KeyboardInterrupt):
        start_render(home, cut_id, {}, detach=False)

    [task] = list_tasks(home)["items"]
    left = sorted(path.name for path in home.cut_media(cut_id).rglob("*"))
    assert (task["error"]["code"], left) == ("interrupted", [])


def test_a_cut_whose_processed_sermon_lost_its_video_is_refused_as_an_internal_error(
    home: Home,
) -> None:
    cut_id = processed_cut(home)
    (home.root / VIDEO_PATH).unlink()

    with pytest.raises(WordcutError) as raised:
        start_render(home, cut_id, {}, detach=False)

    with closing(connect(home)) as connection:
        recorded = renders.of_cut(connection, cut_id)
    left = sorted(path.name for path in home.cut_media(cut_id).rglob("*"))
    assert (raised.value.code, list_tasks(home)["items"], recorded, left) == (
        "internal_error",
        [],
        [],
        [],
    )


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


def test_an_export_whose_record_is_not_committed_leaves_no_file(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    cut_id = processed_cut(home)
    monkeypatch.setattr(render_kind, "connect", lambda home: CommitFails(connect(home)))

    with pytest.raises(WordcutError) as raised:
        start_render(home, cut_id, {}, detach=False)

    with closing(connect(home)) as connection:
        recorded = renders.of_cut(connection, cut_id)
    left = sorted(path.name for path in home.cut_media(cut_id).rglob("*"))
    assert (raised.value.code, recorded, left) == ("internal_error", [], [])


def test_an_estimate_gives_duration_and_options_saving_nothing_even_busy_and_without_video(
    home: Home, lock_owner: StartLockOwner
) -> None:
    cut_id = processed_cut(home)
    (home.root / VIDEO_PATH).unlink()
    lock_owner("process", "sermon 1")
    with closing(connect(home)) as connection:
        before = cuts.by_id(connection, cut_id)

        estimate = estimate_render(connection, cut_id, {"pauses": "short", "caption": False})

        after = cuts.by_id(connection, cut_id)
    assert (sorted(estimate), estimate["options"], after) == (
        ["duration", "options"],
        {**DEFAULT_SUMMARY, "pauses": "short", "caption": False},
        before,
    )


def test_cut_show_lists_the_exports_and_the_options_the_next_one_uses(home: Home) -> None:
    cut_id = processed_cut(home)
    first = rendered(home, cut_id, quality="small")
    second = rendered(home, cut_id, caption=False)

    with closing(connect(home)) as connection:
        shown = show_cut(connection, cut_id, home=home)

    assert (shown["renders"], shown["render_options"]) == (
        [first, second],
        {**DEFAULT_SUMMARY, "quality": "small", "caption": False},
    )
