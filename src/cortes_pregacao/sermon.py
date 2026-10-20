"""Sermon extraction pipeline: live → transcript → frame-accurate sermon cut.

Choosing where the sermon starts and ends is an editorial decision made by
reading the live transcript; this module does the mechanical steps around it.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, replace
from pathlib import Path

from cortes_pregacao.asr import Transcriber
from cortes_pregacao.media import cut_with_fades, duration_seconds, extract_speech_audio
from cortes_pregacao.sermon_folder import SermonFolder
from cortes_pregacao.sync import locate_clip
from cortes_pregacao.transcript import Transcript
from cortes_pregacao.youtube import YouTube

RANGE_MARGIN_S = 60.0  # around an approximate sermon range given by the user
SECTION_MARGIN_S = 30.0  # video downloaded beyond the cut, for sync and keyframes
SYNC_SEARCH_S = 20.0
LEAD_IN_S = 0.3  # before the first word
TAIL_S = 1.5  # after the last word


def transcribe_live(
    youtube: YouTube,
    transcriber: Transcriber,
    url: str,
    folder: SermonFolder,
    approx_start: float | None = None,
    approx_end: float | None = None,
) -> Transcript:
    """Transcribe the live (or an approximate range of it) with live-relative times."""
    folder.create()
    if not folder.live_audio.exists():
        youtube.download_audio(url, folder.live_audio)

    window_start = max(0.0, approx_start - RANGE_MARGIN_S) if approx_start is not None else 0.0
    window_duration = approx_end + RANGE_MARGIN_S - window_start if approx_end else None
    with tempfile.TemporaryDirectory() as tmp:
        audio = extract_speech_audio(
            folder.live_audio, Path(tmp) / "audio.wav", window_start, window_duration
        )
        output = Path(tmp) / "transcript.json"
        transcriber.transcribe(audio, output)
        transcript = Transcript.load(output).shifted(window_start)
    transcript.save(folder.live_words)
    return transcript


@dataclass(frozen=True)
class CutResult:
    live_start: float
    live_end: float
    section_offset_error: float  # real section start minus requested, seconds
    words: int

    @property
    def duration(self) -> float:
        return self.live_end - self.live_start


def cut_sermon(
    youtube: YouTube, url: str, folder: SermonFolder, first_word: float, last_word: float
) -> CutResult:
    """Cut the sermon from ``first_word`` to ``last_word`` (live times, seconds).

    Downloads the video section, syncs it to the live audio, encodes the
    sermon with fades and writes its word transcript rebased to the cut.
    """
    live = Transcript.load(folder.live_words)
    start, end = first_word - LEAD_IN_S, last_word + TAIL_S
    requested = start - SECTION_MARGIN_S
    if not folder.section_video.exists():
        youtube.download_section(url, requested, end + SECTION_MARGIN_S, folder.section_video)

    section_start = locate_clip(
        folder.live_audio, folder.section_video, expected_start=requested, search=SYNC_SEARCH_S
    )
    section_end = section_start + duration_seconds(folder.section_video)
    if not section_start <= start < end <= section_end:
        raise ValueError(f"{folder.section_video} não cobre o trecho; apague-o para baixar de novo")

    cut_with_fades(
        folder.section_video, start - section_start, end - section_start, folder.sermon_video
    )
    words = live.between(start, end)
    words = replace(words, metadata={**words.metadata, "source": url, "source_offset": start})
    words.save(folder.words)
    return CutResult(start, end, section_start - requested, len(words.words))
