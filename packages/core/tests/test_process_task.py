from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut import processing
from wordcut.db import connect, cuts, renders, sermons, tasks, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.renders import NewRender
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.processing import OnProgress
from wordcut.service.sermons import create_sermon, show_sermon, trim_sermon
from wordcut.service.settings import update_settings
from wordcut.tasks import BUILTIN_KIND_MODULES, Progress, Resource, execution, kind
from wordcut.tasks.execution import start
from wordcut.transcript import Transcript, Word
from wordcut.youtube import LiveInfo

LINK = "https://youtu.be/Ab3_x-9QzLk"
FINISHED_LIVE = LiveInfo(
    title="Culto de domingo",
    service_date=date(2026, 10, 18),
    duration=7718.0,
    live_status="was_live",
)
# The section is synced to start at 970 s of the live, exactly where it was requested.
SECTION_START = 970.0


class FakeLive:
    def info(self, url: str) -> LiveInfo:
        return FINISHED_LIVE


class FakeGateways:
    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        return output

    def download_audio_window(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        return output

    def locate(self, recording: Path, clip: Path, expected_start: float, search: float) -> float:
        return expected_start

    def transcribe(self, media: Path, workdir: Path, *, on_progress: OnProgress) -> Transcript:
        words = (Word("Irmãos", 1000.0, 1000.4), Word("Amém.", 1098.5, 1100.0))
        shifted = tuple(word.shifted(-SECTION_START) for word in words)
        return Transcript(words=shifted, language="pt", model="fake")

    def duration(self, media: Path) -> float:
        return 200.0

    def cut(self, source: Path, start: float, end: float, output: Path) -> Path:
        output.write_bytes(b"sermon")
        return output


@pytest.fixture
def home(wordcut_home: Path, monkeypatch: pytest.MonkeyPatch) -> Home:
    monkeypatch.setattr(processing, "default_gateways", lambda whisper_model: FakeGateways())
    return Home(wordcut_home)


def trimmed_sermon(home: Home) -> int:
    with closing(connect(home)) as connection:
        sermon_id: int = create_sermon(
            connection, FakeLive(), LINK, start=1000.0, end=1100.0, home=home
        )["id"]
    return sermon_id


def run_task(home: Home, sermon_id: int, **listen: Any) -> Any:
    return start(home, "process", Resource("sermon", sermon_id), {"force": False}, **listen)


def test_process_is_a_builtin_kind_that_holds_the_processing_lock() -> None:
    assert ("wordcut.tasks.process" in BUILTIN_KIND_MODULES, kind("process").needs_lock) == (
        True,
        True,
    )


def test_the_task_reports_each_stage_up_to_saving(home: Home) -> None:
    sermon_id = trimmed_sermon(home)
    heard: list[Progress] = []

    run_task(home, sermon_id, detach=False, on_progress=heard.append)

    assert [(progress.fraction, progress.message) for progress in heard] == [
        (0.0, "baixando"),
        (0.3, "sincronizando"),
        (0.35, "transcrevendo"),
        (0.85, "cortando"),
        (0.95, "gravando"),
        (0.96, "sugerindo"),
    ]


class HalfwayDownload(FakeGateways):
    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        on_progress(0.5)
        return output


def test_the_task_stores_progress_within_the_downloading_stage(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(processing, "default_gateways", lambda whisper_model: HalfwayDownload())
    monkeypatch.setattr(execution, "PROGRESS_STORE_INTERVAL_SECONDS", 0.0)
    sermon_id = trimmed_sermon(home)
    stored: list[tuple[float, str | None]] = []

    def read_stored(progress: Progress) -> None:
        with closing(connect(home)) as connection:
            task = tasks.by_id(connection, progress.task_id)
        assert task is not None
        stored.append((task.progress, task.progress_message))

    run_task(home, sermon_id, detach=False, on_progress=read_stored)

    assert stored[:3] == [
        (0.0, "baixando"),
        (pytest.approx(0.14), "baixando"),
        (0.3, "sincronizando"),
    ]


def test_the_task_result_is_the_processed_sermon_as_shown_without_its_last_task(
    home: Home,
) -> None:
    sermon_id = trimmed_sermon(home)

    task = run_task(home, sermon_id, detach=False)

    with closing(connect(home)) as connection:
        shown = show_sermon(connection, sermon_id, home=home)
    del shown["last_task"]
    assert task.result == {**shown, "suggestion_warnings": []}


@pytest.mark.parametrize(
    ("configured", "used"), [(None, "large-v3"), ("medium", "medium")], ids=["default", "set"]
)
def test_the_task_transcribes_with_the_configured_whisperx_model(
    home: Home, monkeypatch: pytest.MonkeyPatch, configured: str | None, used: str
) -> None:
    models: list[str] = []

    def gateways(whisper_model: str) -> FakeGateways:
        models.append(whisper_model)
        return FakeGateways()

    monkeypatch.setattr(processing, "default_gateways", gateways)
    sermon_id = trimmed_sermon(home)
    if configured is not None:
        with closing(connect(home)) as connection:
            update_settings(connection, whisper_model=configured)

    run_task(home, sermon_id, detach=False)

    assert models == [used]


class WordsInsideTheBorders(FakeGateways):
    """Words that start and end inside the live borders, so the fitted borders differ."""

    def transcribe(self, media: Path, workdir: Path, *, on_progress: OnProgress) -> Transcript:
        words = (Word("Irmãos", 1002.5, 1003.0), Word("Amém.", 1096.0, 1097.5))
        shifted = tuple(word.shifted(-SECTION_START) for word in words)
        return Transcript(words=shifted, language="pt", model="fake")


class FailingTranscription(FakeGateways):
    def transcribe(self, media: Path, workdir: Path, *, on_progress: OnProgress) -> Transcript:
        raise RuntimeError("WhisperX quebrou")


def processed_borders(home: Home, sermon_id: int) -> tuple[float | None, float | None]:
    with closing(connect(home)) as connection:
        row = sermons.by_id(connection, sermon_id)
    assert row is not None
    return row.processed_live_start, row.processed_live_end


def test_a_successful_processing_keeps_the_live_borders_it_used_as_the_processed_ones(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        processing, "default_gateways", lambda whisper_model: WordsInsideTheBorders()
    )
    sermon_id = trimmed_sermon(home)

    run_task(home, sermon_id, detach=False)

    assert processed_borders(home, sermon_id) == (1000.0, 1100.0)


def test_a_failed_reprocessing_keeps_the_borders_of_the_last_successful_one(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    sermon_id = trimmed_sermon(home)
    run_task(home, sermon_id, detach=False)
    with closing(connect(home)) as connection:
        trim_sermon(connection, sermon_id, 1010.0, 1100.0)
    monkeypatch.setattr(
        processing, "default_gateways", lambda whisper_model: FailingTranscription()
    )

    with pytest.raises(WordcutError):
        start(home, "process", Resource("sermon", sermon_id), {"force": True}, detach=False)

    assert processed_borders(home, sermon_id) == (1000.0, 1100.0)


def test_a_successful_reprocessing_after_a_border_change_clears_the_change(home: Home) -> None:
    sermon_id = trimmed_sermon(home)
    run_task(home, sermon_id, detach=False)
    with closing(connect(home)) as connection:
        trim_sermon(connection, sermon_id, 1010.0, 1100.0)

    start(home, "process", Resource("sermon", sermon_id), {"force": True}, detach=False)

    with closing(connect(home)) as connection:
        assert show_sermon(connection, sermon_id, home=home)["borders_changed"] is False


def exported_cut_file(home: Home, sermon_id: int) -> Path:
    """A cut of the processed sermon with one export, its file on disk."""
    moment = datetime(2026, 10, 27, tzinfo=timezone.utc)
    with closing(connect(home)) as connection, connection:
        [first, *_, last] = [word.id for word in transcripts.words_of(connection, sermon_id)]
        new = NewCut("chosen", "Corte", (Segment(first, last),), first, last, "admin", None)
        [cut_id] = cuts.insert_many(connection, sermon_id, [new], moment)
        render_id = renders.insert(connection, NewRender(cut_id, "", 31.5, {}, moment))
        file = home.cut_media(cut_id) / f"{render_id}.mp4"
        renders.set_path(connection, render_id, str(file.relative_to(home.root)))
    file.parent.mkdir(parents=True)
    file.write_bytes(b"exported cut")
    return file


def test_a_reprocessing_deletes_the_export_files_of_the_cuts_it_removes(home: Home) -> None:
    sermon_id = trimmed_sermon(home)
    run_task(home, sermon_id, detach=False)
    file = exported_cut_file(home, sermon_id)

    start(home, "process", Resource("sermon", sermon_id), {"force": True}, detach=False)

    assert not file.parent.exists()
