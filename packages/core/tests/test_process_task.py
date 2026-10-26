from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from wordcut import processing
from wordcut.db import connect
from wordcut.home import Home
from wordcut.service.sermons import create_sermon, show_sermon
from wordcut.service.settings import update_settings
from wordcut.tasks import BUILTIN_KIND_MODULES, Progress, Resource, kind
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
    def download_section(self, url: str, start: float, end: float, output: Path) -> Path:
        return output

    def download_audio_window(self, url: str, start: float, end: float, output: Path) -> Path:
        return output

    def locate(self, recording: Path, clip: Path, expected_start: float, search: float) -> float:
        return expected_start

    def transcribe(self, media: Path, workdir: Path) -> Transcript:
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
        sermon_id: int = create_sermon(connection, FakeLive(), LINK, start=1000.0, end=1100.0)["id"]
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
