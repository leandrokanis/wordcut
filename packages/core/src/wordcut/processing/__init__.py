"""Processing of a sermon: from the borders in the live to its video, words and sentences.

``pipeline.process`` does the work through ``ProcessingGateways``, the heavy outside world
(YouTube, the transcriber, ffmpeg); ``default_gateways`` builds the real ones, and tests
hand the pipeline doubles instead.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from wordcut.asr import Transcriber
from wordcut.asr.local import LocalTranscriber
from wordcut.media import cut_with_fades, duration_seconds, extract_speech_audio
from wordcut.sync import locate_clip
from wordcut.transcript import Transcript
from wordcut.youtube import YouTube

SPEECH_FILE = "speech.wav"
TRANSCRIPT_FILE = "transcript.json"


class ProcessingGateways(Protocol):
    def download_section(self, url: str, start: float, end: float, output: Path) -> Path:
        """Video and audio of the live between ``start`` and ``end`` (seconds of the live)."""

    def download_audio_window(self, url: str, start: float, end: float, output: Path) -> Path:
        """Only the audio of the live between ``start`` and ``end``, starting exactly there."""

    def locate(self, recording: Path, clip: Path, expected_start: float, search: float) -> float:
        """Seconds into ``recording`` where ``clip`` starts, searched around ``expected_start``."""

    def transcribe(self, media: Path, workdir: Path) -> Transcript:
        """Words spoken in ``media``, with times relative to it; scratch files go in ``workdir``."""

    def duration(self, media: Path) -> float:
        """Length of ``media`` in seconds."""

    def cut(self, source: Path, start: float, end: float, output: Path) -> Path:
        """Frame-accurate cut of ``source`` from ``start`` to ``end`` (its seconds), with fades."""


class LocalGateways:
    """The real outside world: YouTube through yt-dlp, the transcriber and ffmpeg."""

    def __init__(self, youtube: YouTube, transcriber: Transcriber) -> None:
        self._youtube = youtube
        self._transcriber = transcriber

    def download_section(self, url: str, start: float, end: float, output: Path) -> Path:
        return self._youtube.download_section(url, start, end, output)

    def download_audio_window(self, url: str, start: float, end: float, output: Path) -> Path:
        return self._youtube.download_audio_window(url, start, end, output)

    def locate(self, recording: Path, clip: Path, expected_start: float, search: float) -> float:
        return locate_clip(recording, clip, expected_start, search)

    def transcribe(self, media: Path, workdir: Path) -> Transcript:
        audio = extract_speech_audio(media, workdir / SPEECH_FILE)
        output = workdir / TRANSCRIPT_FILE
        self._transcriber.transcribe(audio, output)
        return Transcript.load(output)

    def duration(self, media: Path) -> float:
        return duration_seconds(media)

    def cut(self, source: Path, start: float, end: float, output: Path) -> Path:
        return cut_with_fades(source, start, end, output)


def default_gateways(whisper_model: str) -> ProcessingGateways:
    """The gateways of a real processing, transcribing with the WhisperX ``whisper_model``."""
    return LocalGateways(YouTube(), LocalTranscriber(whisper_model))
