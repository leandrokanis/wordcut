import os
import signal
import subprocess
from collections.abc import Callable, Iterator
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from wordcut import processing
from wordcut.db import connect
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.processing import OnProgress
from wordcut.service.processing import start_processing
from wordcut.service.sermons import create_sermon, list_sermons, show_sermon, trim_sermon
from wordcut.service.tasks import list_tasks, show_task
from wordcut.tasks import runner
from wordcut.transcript import Transcript, Word
from wordcut.youtube import LiveInfo, YouTubeError

LINK = "https://youtu.be/Ab3_x-9QzLk"
FINISHED_LIVE = LiveInfo(
    title="Culto de domingo",
    service_date=date(2026, 10, 18),
    duration=7718.0,
    live_status="was_live",
)
LIVE_START, LIVE_END = 1000.0, 1100.0
# The section download starts at a keyframe 1.75 s before the requested 970 s.
SECTION_START = 968.25
LIVE_WORDS = (
    Word("Irmãos", 1000.0, 1000.4, score=0.91),
    Word("graça.", 1000.5, 1001.0, score=0.88),
    Word("Amém.", 1098.5, 1100.0, score=0.97),
)


LIVE_ON_AIR = LiveInfo.from_metadata(
    {"title": "Culto ao vivo", "timestamp": 1792361083, "live_status": "is_live"}
)


class FakeLive:
    def __init__(self, info: LiveInfo = FINISHED_LIVE) -> None:
        self.answer = info
        self.calls = 0

    def info(self, url: str) -> LiveInfo:
        self.calls += 1
        return self.answer


class FakeGateways:
    """``ProcessingGateways`` double; ``while_transcribing`` runs in the middle of the work."""

    def __init__(self, live_words: tuple[Word, ...] = LIVE_WORDS) -> None:
        self.live_words = live_words
        self.while_transcribing: Callable[[], None] = lambda: None
        self.downloads: list[tuple[float, float]] = []

    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        self.downloads.append((start, end))
        return output

    def download_audio_window(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        return output

    def locate(self, recording: Path, clip: Path, expected_start: float, search: float) -> float:
        return SECTION_START - (LIVE_START - 50)

    def transcribe(self, media: Path, workdir: Path, *, on_progress: OnProgress) -> Transcript:
        self.while_transcribing()
        words = tuple(word.shifted(-SECTION_START) for word in self.live_words)
        return Transcript(words=words, language="pt", model="fake")

    def duration(self, media: Path) -> float:
        return 200.0

    def cut(self, source: Path, start: float, end: float, output: Path) -> Path:
        output.write_bytes(b"sermon")
        return output


@pytest.fixture
def home(wordcut_home: Path) -> Home:
    return Home(wordcut_home)


@pytest.fixture
def gateways(monkeypatch: pytest.MonkeyPatch) -> FakeGateways:
    fake = FakeGateways()
    monkeypatch.setattr(processing, "default_gateways", lambda whisper_model: fake)
    return fake


@pytest.fixture
def opened(home: Home) -> Iterator[Any]:
    with closing(connect(home)) as connection:
        yield connection


def trimmed_sermon(home: Home, live: FakeLive | None = None) -> int:
    with closing(connect(home)) as connection:
        created = create_sermon(
            connection, live or FakeLive(), LINK, home=home, start=LIVE_START, end=LIVE_END
        )
    sermon_id: int = created["id"]
    return sermon_id


def process(home: Home, sermon_id: int, *, force: bool = False) -> None:
    start_processing(home, sermon_id, live=FakeLive(), force=force, detach=False)


def shown(home: Home, sermon_id: int, *, transcript: bool = False) -> dict[str, Any]:
    with closing(connect(home)) as connection:
        return show_sermon(connection, sermon_id, home=home, transcript=transcript)


def test_processing_in_the_foreground_leaves_the_sermon_processed_with_borders_fitted_to_words(
    home: Home, gateways: FakeGateways
) -> None:
    sermon_id = trimmed_sermon(home)

    process(home, sermon_id)

    sermon = shown(home, sermon_id)
    assert (
        sermon["status"],
        sermon["sermon_start"],
        sermon["sermon_end"],
        sermon["processed_at"] is not None,
    ) == ("processed", 999.7, 1101.5, True)


def test_show_with_transcript_lists_the_sentences_in_sermon_time_with_their_words(
    home: Home, gateways: FakeGateways
) -> None:
    sermon_id = trimmed_sermon(home)
    process(home, sermon_id)

    sentences = shown(home, sermon_id, transcript=True)["sentences"]

    first, second = sentences
    assert (
        [(item["start"], item["end"], item["text"]) for item in sentences],
        sorted(first),
        (first["last_word_id"] - first["first_word_id"], second["first_word_id"]),
    ) == (
        [(0.3, 1.3, "Irmãos graça."), (98.8, 100.3, "Amém.")],
        ["end", "first_word_id", "id", "last_word_id", "start", "text"],
        (1, first["last_word_id"] + 1),
    )


def test_show_without_transcript_has_no_sentences(home: Home, gateways: FakeGateways) -> None:
    sermon_id = trimmed_sermon(home)
    process(home, sermon_id)

    assert "sentences" not in shown(home, sermon_id)


def test_media_end_in_the_sermon_folder_and_the_work_files_are_removed(
    home: Home, gateways: FakeGateways
) -> None:
    sermon_id = trimmed_sermon(home)

    process(home, sermon_id)

    folder = home.sermon_media(sermon_id)
    assert ((folder / "sermon.mp4").read_bytes(), (folder / "work").exists()) == (b"sermon", False)


def test_the_sermon_is_processing_while_the_task_works(home: Home, gateways: FakeGateways) -> None:
    sermon_id = trimmed_sermon(home)
    seen: list[str] = []
    gateways.while_transcribing = lambda: seen.append(shown(home, sermon_id)["status"])

    process(home, sermon_id)

    assert seen == ["processing"]


def test_a_detached_processing_answers_at_once_with_the_sermon_already_processing(
    home: Home, harmless_tasks: list[Any]
) -> None:
    sermon_id = trimmed_sermon(home)

    task = start_processing(home, sermon_id, live=FakeLive(), detach=True)

    assert (task.status, task.kind, shown(home, sermon_id)["status"]) == (
        "running",
        "process",
        "processing",
    )


class RefusingYouTube(FakeGateways):
    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        raise YouTubeError("O YouTube recusou o pedido.")


class MissingWhisperX(FakeGateways):
    def transcribe(self, media: Path, workdir: Path, *, on_progress: OnProgress) -> Transcript:
        raise FileNotFoundError("ambiente do WhisperX não encontrado")


class BrokenCut(FakeGateways):
    def cut(self, source: Path, start: float, end: float, output: Path) -> Path:
        raise RuntimeError("ffmpeg quebrou")


@pytest.mark.parametrize(
    ("failing", "code", "exit_code"),
    [
        (RefusingYouTube, "youtube_error", 6),
        (MissingWhisperX, "transcription_error", 6),
        (BrokenCut, "internal_error", 1),
    ],
)
def test_a_failure_leaves_the_task_and_the_sermon_failed_with_its_error(
    failing: type[FakeGateways],
    code: str,
    exit_code: int,
    home: Home,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(processing, "default_gateways", lambda whisper_model: failing())
    sermon_id = trimmed_sermon(home)

    with pytest.raises(WordcutError) as raised:
        process(home, sermon_id)

    [task] = list_tasks(home, kind="process")["items"]
    assert (
        raised.value.code,
        raised.value.exit_code,
        task["status"],
        task["error"]["code"],
        shown(home, sermon_id)["status"],
    ) == (code, exit_code, "failed", code, "failed")


@pytest.mark.parametrize("failing", [RefusingYouTube, MissingWhisperX, BrokenCut])
def test_a_sermon_whose_processing_failed_can_be_trimmed_again_at_once(
    failing: type[FakeGateways], home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(processing, "default_gateways", lambda whisper_model: failing())
    sermon_id = trimmed_sermon(home)
    with pytest.raises(WordcutError):
        process(home, sermon_id)

    with closing(connect(home)) as connection:
        trimmed = trim_sermon(connection, sermon_id, LIVE_START - 5, LIVE_END)

    assert trimmed["status"] == "trimmed"


def test_a_sermon_whose_detached_processing_failed_can_be_trimmed_again_at_once(
    home: Home, harmless_tasks: list[Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(processing, "default_gateways", lambda whisper_model: RefusingYouTube())
    sermon_id = trimmed_sermon(home)
    task = start_processing(home, sermon_id, live=FakeLive(), detach=True)
    runner.main([str(task.id)])

    with closing(connect(home)) as connection:
        trimmed = trim_sermon(connection, sermon_id, LIVE_START - 5, LIVE_END)

    assert trimmed["status"] == "trimmed"


def untrimmed_sermon(home: Home) -> int:
    with closing(connect(home)) as connection:
        sermon_id: int = create_sermon(connection, FakeLive(), LINK, home=home)["id"]
    return sermon_id


def sermon_on_air(home: Home) -> int:
    return trimmed_sermon(home, FakeLive(LIVE_ON_AIR))


def processed_sermon(home: Home) -> int:
    sermon_id = trimmed_sermon(home)
    process(home, sermon_id)
    return sermon_id


def task_count(home: Home) -> int:
    """The processing tasks; creating a sermon also starts preparing its timeline."""
    return len(list_tasks(home, kind="process")["items"])


@pytest.mark.parametrize(
    ("prepare", "code", "exit_code"),
    [
        (untrimmed_sermon, "sermon_not_trimmed", 5),
        (sermon_on_air, "live_not_finished", 5),
        (processed_sermon, "would_discard_edits", 5),
    ],
)
def test_a_sermon_that_cannot_be_processed_is_refused_without_a_task_and_unchanged(
    prepare: Callable[[Home], int],
    code: str,
    exit_code: int,
    home: Home,
    gateways: FakeGateways,
) -> None:
    sermon_id = prepare(home)
    before = (shown(home, sermon_id), task_count(home))

    with pytest.raises(WordcutError) as raised:
        start_processing(home, sermon_id, live=FakeLive(LIVE_ON_AIR), detach=False)

    assert (
        raised.value.code,
        raised.value.exit_code,
        (shown(home, sermon_id), task_count(home)),
    ) == (
        code,
        exit_code,
        before,
    )


def test_processing_an_unknown_sermon_is_not_found_without_a_task(home: Home) -> None:
    with pytest.raises(WordcutError) as raised:
        process(home, 999)

    assert (raised.value.code, raised.value.exit_code, task_count(home)) == ("not_found", 3, 0)


def test_a_live_that_ended_after_the_sermon_was_created_is_looked_up_once_and_processed(
    home: Home, gateways: FakeGateways
) -> None:
    sermon_id = sermon_on_air(home)
    live = FakeLive(FINISHED_LIVE)

    start_processing(home, sermon_id, live=live, detach=False)

    sermon = shown(home, sermon_id)
    assert (live.calls, sermon["live_finished"], sermon["live_duration"], sermon["status"]) == (
        1,
        True,
        7718.0,
        "processed",
    )


def test_a_finished_live_is_not_looked_up_again(home: Home, gateways: FakeGateways) -> None:
    sermon_id = trimmed_sermon(home)
    live = FakeLive()

    start_processing(home, sermon_id, live=live, detach=False)

    assert live.calls == 0


class LiveEndingWhileAnotherProcessingFinishes(FakeLive):
    """Answers that the live ended once another processing of the sermon has finished."""

    def __init__(self, home: Home, sermon_id: int) -> None:
        super().__init__(FINISHED_LIVE)
        self.home, self.sermon_id = home, sermon_id

    def info(self, url: str) -> LiveInfo:
        start_processing(self.home, self.sermon_id, live=FakeLive(), detach=False)
        return super().info(url)


def test_a_sermon_processed_between_the_check_and_the_lock_is_refused_without_a_task(
    home: Home, gateways: FakeGateways
) -> None:
    sermon_id = sermon_on_air(home)

    with pytest.raises(WordcutError) as raised:
        start_processing(
            home,
            sermon_id,
            live=LiveEndingWhileAnotherProcessingFinishes(home, sermon_id),
            detach=False,
        )

    assert (raised.value.code, task_count(home)) == ("would_discard_edits", 1)


StartLockOwner = Callable[[str, str], "subprocess.Popen[str]"]


def test_a_busy_machine_refuses_with_the_holder_without_a_task_and_unchanged(
    home: Home, gateways: FakeGateways, lock_owner: StartLockOwner
) -> None:
    sermon_id = trimmed_sermon(home)
    before = shown(home, sermon_id)
    lock_owner("render", "cut 34")

    with pytest.raises(WordcutError) as raised:
        process(home, sermon_id)

    assert (
        raised.value.code,
        raised.value.exit_code,
        (raised.value.details or {}).get("kind"),
        task_count(home),
        shown(home, sermon_id),
    ) == ("busy", 4, "render", 0, before)


def test_a_sermon_being_processed_refuses_another_processing_as_busy(
    home: Home, harmless_tasks: list[Any]
) -> None:
    sermon_id = trimmed_sermon(home)
    running = start_processing(home, sermon_id, live=FakeLive(), detach=True)

    with pytest.raises(WordcutError) as raised:
        process(home, sermon_id)

    assert (raised.value.code, (raised.value.details or {}).get("task_id"), task_count(home)) == (
        "busy",
        running.id,
        1,
    )


class FailingOnce(FakeGateways):
    def __init__(self) -> None:
        super().__init__()
        self.failures = 1

    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        if self.failures:
            self.failures -= 1
            raise YouTubeError("O YouTube recusou o pedido.")
        return super().download_section(url, start, end, output, on_progress=on_progress)


def test_a_failed_sermon_is_processed_again_by_the_same_operation(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateways = FailingOnce()
    monkeypatch.setattr(processing, "default_gateways", lambda whisper_model: gateways)
    sermon_id = trimmed_sermon(home)
    with pytest.raises(WordcutError):
        process(home, sermon_id)

    process(home, sermon_id)

    assert shown(home, sermon_id)["status"] == "processed"


class YtDlpLike(FakeGateways):
    """Keeps a file it finds already downloaded, as yt-dlp does."""

    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        if not output.exists():
            super().download_section(url, start, end, output, on_progress=on_progress)
        return output


def test_a_new_processing_downloads_again_instead_of_using_an_earlier_section(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    gateways = YtDlpLike()
    monkeypatch.setattr(processing, "default_gateways", lambda whisper_model: gateways)
    sermon_id = trimmed_sermon(home)
    stale = home.sermon_media(sermon_id) / "work" / "section.mp4"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"faixa de bordas antigas")

    process(home, sermon_id)

    assert gateways.downloads == [(970.0, 1130.0)]


def sentence_ids(home: Home, sermon_id: int) -> list[int]:
    return [item["id"] for item in shown(home, sermon_id, transcript=True)["sentences"]]


def test_force_discards_the_old_transcript_at_the_start_and_records_a_new_one(
    home: Home, gateways: FakeGateways
) -> None:
    sermon_id = processed_sermon(home)
    old = sentence_ids(home, sermon_id)
    during: list[list[int]] = []
    gateways.while_transcribing = lambda: during.append(sentence_ids(home, sermon_id))

    process(home, sermon_id, force=True)

    new = sentence_ids(home, sermon_id)
    assert (during, len(new), set(old) & set(new), shown(home, sermon_id)["status"]) == (
        [[]],
        len(old),
        set(),
        "processed",
    )


def killed(process: "subprocess.Popen[bytes]") -> None:
    """End the task process as a machine restart would, and reap it."""
    os.killpg(process.pid, signal.SIGKILL)
    process.wait()


def test_a_sermon_whose_task_process_died_is_read_failed_with_its_task_interrupted(
    home: Home, harmless_tasks: list[Any]
) -> None:
    sermon_id = trimmed_sermon(home)
    start_processing(home, sermon_id, live=FakeLive(), detach=True)
    killed(harmless_tasks[-1])

    sermon = shown(home, sermon_id)

    assert (
        sermon["status"],
        sermon["last_task"]["status"],
        sermon["last_task"]["error"]["code"],
    ) == ("failed", "failed", "interrupted")


def test_listing_processing_sermons_leaves_out_one_whose_task_process_died(
    home: Home, harmless_tasks: list[Any]
) -> None:
    sermon_id = trimmed_sermon(home)
    start_processing(home, sermon_id, live=FakeLive(), detach=True)
    killed(harmless_tasks[-1])

    with closing(connect(home)) as connection:
        assert list_sermons(connection, "processing", home=home) == {"items": []}


def test_last_task_is_the_sermons_latest_task_as_task_show_gives_it(
    home: Home, gateways: FakeGateways
) -> None:
    sermon_id = trimmed_sermon(home)
    task = start_processing(home, sermon_id, live=FakeLive(), detach=False)

    assert shown(home, sermon_id)["last_task"] == show_task(home, task.id)
