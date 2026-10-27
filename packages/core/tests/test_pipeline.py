import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from wordcut.errors import WordcutError
from wordcut.processing import pipeline
from wordcut.transcript import Transcript, Word
from wordcut.youtube import YouTube, YouTubeError

OnProgress = Callable[[float], None]

LINK = "https://youtu.be/Ab3_x-9QzLk"
LIVE_START = 1000.0
LIVE_END = 1100.0
LIVE_DURATION = 7718.0
# The section download starts at a keyframe 1.75 s before the requested 970 s.
REAL_SECTION_START = 968.25
SECTION_SECONDS = 161.75

LIVE_WORDS = (
    Word("antes", 999.99, 1000.0),
    Word("Irmãos", 1000.0, 1000.4, score=0.91),
    Word("graça.", 1000.5, 1001.0, score=0.88, estimated=True),
    Word("Amém.", 1098.5, 1100.0, score=0.97),
    Word("depois", 1100.0, 1100.5),
)


def in_section(*live_words: Word) -> tuple[Word, ...]:
    """The words as the transcriber of the downloaded section hears them."""
    return tuple(word.shifted(-REAL_SECTION_START) for word in live_words)


@dataclass
class FakeGateways:
    """``ProcessingGateways`` double: records the calls and answers known values."""

    sync_offset: float = REAL_SECTION_START - (LIVE_START - 50)
    section_seconds: float = SECTION_SECONDS
    section_words: tuple[Word, ...] = in_section(*LIVE_WORDS)
    section_progress: tuple[float, ...] = ()
    window_progress: tuple[float, ...] = ()
    transcription_progress: tuple[float, ...] = ()
    calls: list[tuple[object, ...]] = field(default_factory=list)

    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        self.calls.append(("download_section", url, start, end))
        for fraction in self.section_progress:
            on_progress(fraction)
        return output

    def download_audio_window(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        self.calls.append(("download_audio_window", url, start, end))
        for fraction in self.window_progress:
            on_progress(fraction)
        return output

    def locate(self, recording: Path, clip: Path, expected_start: float, search: float) -> float:
        self.calls.append(("locate", recording.name, clip.name, expected_start, search))
        return self.sync_offset

    def transcribe(self, media: Path, workdir: Path, *, on_progress: OnProgress) -> Transcript:
        self.calls.append(("transcribe", media.name))
        for fraction in self.transcription_progress:
            on_progress(fraction)
        return Transcript(words=self.section_words, language="pt", model="fake")

    def duration(self, media: Path) -> float:
        return self.section_seconds

    def cut(self, source: Path, start: float, end: float, output: Path) -> Path:
        self.calls.append(("cut", source.name, start, end, output))
        return output

    def named(self, name: str) -> list[tuple[object, ...]]:
        return [call[1:] for call in self.calls if call[0] == name]


def run(
    gateways: FakeGateways,
    workdir: Path,
    live_start: float = LIVE_START,
    live_end: float = LIVE_END,
    live_duration: float | None = LIVE_DURATION,
) -> pipeline.Processed:
    return pipeline.process(
        gateways,
        workdir,
        LINK,
        live_start,
        live_end,
        lambda fraction, message: None,
        live_duration=live_duration,
    )


def test_the_cut_spans_from_before_the_first_word_to_after_the_last_in_the_section_time(
    tmp_path: Path,
) -> None:
    gateways = FakeGateways()

    run(gateways, tmp_path)

    [(source, start, end, output)] = gateways.named("cut")
    assert (source, start, end, output) == (
        "section.mp4",
        pytest.approx(1000.0 - 0.3 - REAL_SECTION_START),
        pytest.approx(1100.0 + 1.5 - REAL_SECTION_START),
        tmp_path / "sermon.mp4",
    )


@pytest.mark.parametrize(
    ("borders", "live_duration", "downloads"),
    [
        (
            (1000.0, 1100.0),
            LIVE_DURATION,
            [(LINK, 970.0, 1130.0), (LINK, 950.0, 1040.0)],
        ),
        ((10.0, 100.0), 120.0, [(LINK, 0.0, 120.0), (LINK, 0.0, 50.0)]),
        ((1000.0, 1100.0), None, [(LINK, 970.0, 1130.0), (LINK, 950.0, 1040.0)]),
    ],
)
def test_only_the_section_around_the_borders_and_the_sync_window_are_downloaded_within_the_live(
    borders: tuple[float, float],
    live_duration: float | None,
    downloads: list[tuple[object, ...]],
    tmp_path: Path,
) -> None:
    gateways = FakeGateways(section_words=(Word("Irmãos", 40.0, 40.4), Word("Amém.", 60.0, 61.0)))

    run(gateways, tmp_path, *borders, live_duration=live_duration)

    assert [call for call in gateways.calls if call[0].startswith("download")] == [
        ("download_section", *downloads[0]),
        ("download_audio_window", *downloads[1]),
    ]


@pytest.mark.parametrize(("live_start", "expected_start"), [(1000.0, 20.0), (10.0, 0.0)])
def test_the_section_is_located_inside_the_audio_window_around_where_it_was_requested(
    live_start: float, expected_start: float, tmp_path: Path
) -> None:
    gateways = FakeGateways(section_words=(Word("Irmãos", 40.0, 40.4), Word("Amém.", 60.0, 61.0)))

    run(gateways, tmp_path, live_start, live_start + 100.0)

    assert gateways.named("locate") == [("window.m4a", "section.mp4", expected_start, 20.0)]


def test_words_are_kept_from_the_first_to_the_last_inside_the_borders_in_sermon_time_to_the_ms(
    tmp_path: Path,
) -> None:
    processed = run(FakeGateways(), tmp_path)

    assert processed.words == (
        Word("Irmãos", 0.3, 0.7, score=0.91),
        Word("graça.", 0.8, 1.3, score=0.88, estimated=True),
        Word("Amém.", 98.8, 100.3, score=0.97),
    )


def test_borders_fitted_to_the_words_are_given_in_live_time(tmp_path: Path) -> None:
    processed = run(FakeGateways(), tmp_path)

    assert (processed.sermon_start, processed.sermon_end) == (999.7, 1101.5)


def test_sentences_are_made_from_the_kept_words_in_sermon_time(tmp_path: Path) -> None:
    processed = run(FakeGateways(), tmp_path)

    assert [
        (sentence.first_word, sentence.last_word, sentence.text, sentence.start, sentence.end)
        for sentence in processed.sentences
    ] == [(0, 1, "Irmãos graça.", 0.3, 1.3), (2, 2, "Amém.", 98.8, 100.3)]


@pytest.mark.parametrize(
    "section_words",
    [
        (),
        in_section(Word("antes", 990.0, 999.0), Word("depois", 1100.5, 1101.0)),
        in_section(Word("atravessa", 999.0, 1101.0)),
    ],
)
def test_no_word_inside_the_borders_is_a_processing_error_without_a_cut(
    section_words: tuple[Word, ...], tmp_path: Path
) -> None:
    gateways = FakeGateways(section_words=section_words)

    with pytest.raises(WordcutError) as raised:
        run(gateways, tmp_path)

    assert (raised.value.code, raised.value.exit_code, gateways.named("cut")) == (
        "processing_error",
        1,
        [],
    )


@pytest.mark.parametrize(
    "gateways",
    [
        FakeGateways(section_seconds=100.0),
        # Synced to start at the first border, so the lead-in before the first word is missing.
        FakeGateways(
            sync_offset=50.0, section_words=(Word("Irmãos", 0.1, 0.5), Word("Amém.", 60.0, 61.0))
        ),
    ],
)
def test_a_cut_outside_the_downloaded_section_is_a_processing_error_without_a_cut(
    gateways: FakeGateways, tmp_path: Path
) -> None:
    with pytest.raises(WordcutError) as raised:
        run(gateways, tmp_path)

    assert (raised.value.code, gateways.named("cut")) == ("processing_error", [])


class RefusedDownload(FakeGateways):
    def download_audio_window(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        raise YouTubeError("O YouTube recusou o pedido.")


def test_a_youtube_failure_is_a_youtube_error_with_exit_6(tmp_path: Path) -> None:
    gateways = RefusedDownload()

    with pytest.raises(WordcutError) as raised:
        run(gateways, tmp_path)

    assert (raised.value.code, raised.value.exit_code, gateways.named("cut")) == (
        "youtube_error",
        6,
        [],
    )


@dataclass
class FailingTranscription(FakeGateways):
    failure: Exception = field(default_factory=lambda: FileNotFoundError("sem ambiente"))

    def transcribe(self, media: Path, workdir: Path, *, on_progress: OnProgress) -> Transcript:
        raise self.failure


@pytest.mark.parametrize(
    "failure",
    [
        FileNotFoundError("ambiente do WhisperX não encontrado"),
        subprocess.CalledProcessError(1, ["python", "-m", "wordcut.asr.worker"]),
    ],
)
def test_a_transcriber_failure_is_a_transcription_error_with_exit_6(
    failure: Exception, tmp_path: Path
) -> None:
    gateways = FailingTranscription(failure=failure)

    with pytest.raises(WordcutError) as raised:
        run(gateways, tmp_path)

    assert (raised.value.code, raised.value.exit_code, gateways.named("cut")) == (
        "transcription_error",
        6,
        [],
    )


def test_progress_names_each_stage_in_portuguese_within_the_planned_fractions(
    tmp_path: Path,
) -> None:
    heard: list[tuple[float, str]] = []

    pipeline.process(
        FakeGateways(),
        tmp_path,
        LINK,
        LIVE_START,
        LIVE_END,
        lambda fraction, message: heard.append((fraction, message)),
        live_duration=LIVE_DURATION,
    )

    assert heard == [
        (0.0, "baixando"),
        (0.3, "sincronizando"),
        (0.35, "transcrevendo"),
        (0.85, "cortando"),
    ]


def heard_progress(gateways: FakeGateways, workdir: Path) -> list[tuple[float, str]]:
    heard: list[tuple[float, str]] = []
    pipeline.process(
        gateways,
        workdir,
        LINK,
        LIVE_START,
        LIVE_END,
        lambda fraction, message: heard.append((fraction, message)),
        live_duration=LIVE_DURATION,
    )
    return heard


def test_section_download_progress_rises_within_the_downloading_stage(tmp_path: Path) -> None:
    heard = heard_progress(FakeGateways(section_progress=(0.5, 1.0)), tmp_path)

    assert heard[:3] == [
        (0.0, "baixando"),
        (pytest.approx(0.14), "baixando"),
        (pytest.approx(0.28), "baixando"),
    ]


def test_transcription_progress_rises_within_the_transcribing_stage(tmp_path: Path) -> None:
    heard = heard_progress(FakeGateways(transcription_progress=(0.5,)), tmp_path)

    assert heard[2:4] == [(0.35, "transcrevendo"), (pytest.approx(0.6), "transcrevendo")]


def test_progress_beyond_the_whole_operation_stops_at_the_end_of_its_part(tmp_path: Path) -> None:
    heard = heard_progress(FakeGateways(section_progress=(1.5,)), tmp_path)

    assert heard[1] == (pytest.approx(0.28), "baixando")


def test_progress_lower_than_what_was_reached_is_ignored(tmp_path: Path) -> None:
    heard = heard_progress(FakeGateways(section_progress=(0.5, 0.25, 0.75)), tmp_path)

    assert [fraction for fraction, message in heard if message == "baixando"] == [
        0.0,
        pytest.approx(0.14),
        pytest.approx(0.21),
    ]


def test_the_audio_window_download_fills_the_end_of_the_downloading_stage(
    tmp_path: Path,
) -> None:
    heard = heard_progress(
        FakeGateways(section_progress=(1.0,), window_progress=(0.0, 0.5, 1.0)), tmp_path
    )

    assert [fraction for fraction, message in heard if message == "baixando"] == [
        0.0,
        pytest.approx(0.28),
        pytest.approx(0.29),
        pytest.approx(0.3),
    ]


@dataclass
class SectionFromYtDlp(FakeGateways):
    """Downloads the section through the real yt-dlp adapter, run as a process printing
    what yt-dlp and its ffmpeg print for a section downloaded by a single ffmpeg."""

    yt_dlp_lines: tuple[str, ...] = ()
    cookies: Path = Path()

    def download_section(
        self, url: str, start: float, end: float, output: Path, *, on_progress: OnProgress
    ) -> Path:
        script = f"for line in {list(self.yt_dlp_lines)!r}:\n    print(line)"
        source = YouTube(
            cookies=self.cookies, ffmpeg_dir=None, program=(sys.executable, "-c", script)
        )
        return source.download_section(url, start, end, output, on_progress=on_progress)


def test_section_downloaded_by_a_single_ffmpeg_reaches_the_end_of_its_part_before_the_window(
    tmp_path: Path,
) -> None:
    cookies = tmp_path / "youtube-cookies.txt"
    cookies.write_text("# fictício\n")
    # The section asked around the borders is 160 s long (970 s to 1130 s of the live).
    gateways = SectionFromYtDlp(
        yt_dlp_lines=("out_time_us=80000000", "out_time_us=160000000", "wordcut-progress 9 9 NA"),
        cookies=cookies,
    )

    heard = heard_progress(gateways, tmp_path)

    assert max(fraction for fraction, message in heard if message == "baixando") == (
        pytest.approx(0.28)
    )
