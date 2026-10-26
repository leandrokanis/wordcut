"""The processing pipeline: download the borders, sync, transcribe, fit to words and cut."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

from wordcut.errors import WordcutError
from wordcut.processing import ProcessingGateways
from wordcut.processing.sentences import Sentence, split_sentences
from wordcut.transcript import Word
from wordcut.youtube import YouTubeError

# The audio window is downloaded exactly, so it is the ruler the section is synced against.
WINDOW_BEFORE_S = 50.0
WINDOW_AFTER_S = 40.0

SECTION_MARGIN_S = 30.0  # video downloaded beyond the cut, for sync and keyframes
SYNC_SEARCH_S = 20.0
LEAD_IN_S = 0.3  # before the first word
TAIL_S = 1.5  # after the last word

SECTION_FILE = "section.mp4"
WINDOW_FILE = "window.m4a"
CUT_FILE = "sermon.mp4"
# Times are kept to the millisecond, the precision of HH:MM:SS.mmm (docs/cli.md §2).
MILLISECOND_DIGITS = 3

# Each stage: the fraction of the processing done when it starts, and its message.
DOWNLOADING = (0.0, "baixando")
SYNCING = (0.3, "sincronizando")
TRANSCRIBING = (0.35, "transcrevendo")
CUTTING = (0.85, "cortando")

Progress = Callable[[float, str], None]


@dataclass(frozen=True)
class Processed:
    """What processing made: ``words`` and ``sentences`` in sermon time (0 at
    ``sermon_start``), the borders fitted to the words in live time and the cut video."""

    words: tuple[Word, ...]
    sentences: list[Sentence]
    sermon_start: float
    sermon_end: float
    video: Path


def process(
    gateways: ProcessingGateways,
    workdir: Path,
    url: str,
    live_start: float,
    live_end: float,
    progress: Progress,
    *,
    live_duration: float | None = None,
) -> Processed:
    """Process the sermon between ``live_start`` and ``live_end`` (seconds of the live).

    Only the section of the live around the borders and a short audio window are
    downloaded into ``workdir``; the cut video is left there as ``sermon.mp4``.
    """
    progress(*DOWNLOADING)
    downloaded = _download(gateways, workdir, url, live_start, live_end, _Live(live_duration))
    progress(*SYNCING)
    offset = gateways.locate(
        downloaded.window, downloaded.section, downloaded.expected_offset, SYNC_SEARCH_S
    )
    section_start = downloaded.window_start + offset
    progress(*TRANSCRIBING)
    with _transcription_errors():
        transcript = gateways.transcribe(downloaded.section, workdir)
    kept = _within(transcript.shifted(section_start).words, live_start, live_end)
    sermon_start = _to_millisecond(kept[0].start - LEAD_IN_S)
    sermon_end = _to_millisecond(kept[-1].end + TAIL_S)
    progress(*CUTTING)
    video = _cut(
        gateways,
        downloaded.section,
        sermon_start - section_start,
        sermon_end - section_start,
        workdir / CUT_FILE,
    )
    words = tuple(_word_to_millisecond(word.shifted(-sermon_start)) for word in kept)
    return Processed(words, split_sentences(words), sermon_start, sermon_end, video)


@dataclass(frozen=True)
class _Downloaded:
    """The section and the audio window; ``expected_offset`` is where the section was
    requested to start, in seconds of the window."""

    section: Path
    window: Path
    window_start: float
    expected_offset: float


def _download(
    gateways: ProcessingGateways,
    workdir: Path,
    url: str,
    live_start: float,
    live_end: float,
    live: _Live,
) -> _Downloaded:
    section_start = live.clamped(live_start - SECTION_MARGIN_S)
    window_start = live.clamped(live_start - WINDOW_BEFORE_S)
    with _youtube_errors():
        section = gateways.download_section(
            url, section_start, live.clamped(live_end + SECTION_MARGIN_S), workdir / SECTION_FILE
        )
        window = gateways.download_audio_window(
            url, window_start, live.clamped(live_start + WINDOW_AFTER_S), workdir / WINDOW_FILE
        )
    return _Downloaded(section, window, window_start, section_start - window_start)


def _cut(
    gateways: ProcessingGateways, section: Path, start: float, end: float, output: Path
) -> Path:
    """Cut ``section`` from ``start`` to ``end`` (its seconds), once they fit inside it."""
    if start < 0 or end > gateways.duration(section):
        raise WordcutError(
            "processing_error",
            "O vídeo baixado não cobre a pregação inteira; processe de novo.",
            {"cut_start": start, "cut_end": end},
        )
    return gateways.cut(section, start, end, output)


@contextmanager
def _youtube_errors() -> Iterator[None]:
    try:
        yield
    except YouTubeError as error:
        raise WordcutError("youtube_error", str(error)) from None


@contextmanager
def _transcription_errors() -> Iterator[None]:
    """The transcriber fails without its environment (``FileNotFoundError``) or when the
    worker process fails, out of GPU memory for instance."""
    try:
        yield
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise WordcutError(
            "transcription_error",
            "A transcrição falhou: confira o ambiente do WhisperX e a GPU (veja o README).",
        ) from None


@dataclass(frozen=True)
class _Live:
    """The live's timeline; ``duration`` is ``None`` while unknown."""

    duration: float | None

    def clamped(self, moment: float) -> float:
        """``moment`` kept between 0 and the end of the live."""
        latest = moment if self.duration is None else min(moment, self.duration)
        return max(0.0, latest)


def _within(words: tuple[Word, ...], live_start: float, live_end: float) -> tuple[Word, ...]:
    """From the first word starting at or after ``live_start`` to the last one ending at or
    before ``live_end``."""
    first = next((index for index, word in enumerate(words) if word.start >= live_start), None)
    last = max((index for index, word in enumerate(words) if word.end <= live_end), default=None)
    if first is None or last is None or last < first:
        raise WordcutError(
            "processing_error",
            "Nenhuma palavra foi ouvida dentro das bordas; confira as bordas da pregação.",
            {"live_start": live_start, "live_end": live_end},
        )
    return words[first : last + 1]


def _word_to_millisecond(word: Word) -> Word:
    return replace(word, start=_to_millisecond(word.start), end=_to_millisecond(word.end))


def _to_millisecond(seconds: float) -> float:
    return round(seconds, MILLISECOND_DIGITS)
