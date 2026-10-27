"""The media of a sermon's timeline: thumbnails of the live and the peaks of its waveform
(ADR-0025).

``prepare`` does the work through ``TimelineMediaGateways``, the outside world (YouTube and
ffmpeg); ``default_gateways`` builds the real ones, and tests hand ``prepare`` doubles
instead. ``store`` keeps what ``prepare`` made in the sermon's media folder, where the
``read_*`` functions find it.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from wordcut import network
from wordcut.errors import WordcutError
from wordcut.timeline_media import waveform
from wordcut.timeline_media.storyboard import Storyboard, build_storyboard
from wordcut.youtube import YouTube, YouTubeError

# Peaks of the whole live: more than the widest timeline has pixels at its default zoom.
PEAK_BUCKETS = 4000
AUDIO_FILE = "audio"
STORYBOARD_FOLDER = "storyboard"

THUMBNAILS_IMAGE = "thumbnails.jpg"
THUMBNAILS_LAYOUT = "thumbnails.json"
WAVEFORM_FILE = "waveform.json"
# Peaks are kept to this many decimals: finer than a pixel of the tallest track.
PEAK_DIGITS = 3

# How far the preparation is, from 0 to 1, and what it is doing, in Portuguese.
OnStage = Callable[[float, str], None]
THUMBNAILS_STAGE = (0.0, "miniaturas")
AUDIO_STAGE = (0.3, "áudio")
WAVEFORM_STAGE = (0.8, "forma de onda")

# What a storyboard that cannot be built raises; the timeline then goes without thumbnails.
STORYBOARD_FAILURES = (YouTubeError, WordcutError, OSError, ValueError, KeyError)


class TimelineMediaGateways(Protocol):
    def storyboard(self, url: str, out_dir: Path) -> Storyboard | None:
        """The thumbnail strip of the live, written in ``out_dir``; ``None`` if it has none."""

    def audio(self, url: str, output: Path) -> Path:
        """Only the audio of the whole live, in its lowest quality."""

    def peaks(self, audio: Path, buckets: int) -> list[float]:
        """The peaks of ``audio`` in ``buckets`` equal stretches, from 0 to 1."""


@dataclass(frozen=True)
class Prepared:
    peaks: list[float]
    storyboard: Storyboard | None


def prepare(
    gateways: TimelineMediaGateways, workdir: Path, url: str, on_stage: OnStage | None = None
) -> Prepared:
    """The thumbnails and the peaks of the live at ``url``, made in ``workdir``.

    A storyboard that fails leaves the timeline with only the waveform; the audio failing
    raises. The audio is deleted once its peaks are known.
    """
    tell = on_stage or (lambda fraction, message: None)
    tell(*THUMBNAILS_STAGE)
    strip = _storyboard(gateways, url, workdir / STORYBOARD_FOLDER)
    tell(*AUDIO_STAGE)
    audio = gateways.audio(url, workdir / AUDIO_FILE)
    try:
        tell(*WAVEFORM_STAGE)
        found = gateways.peaks(audio, PEAK_BUCKETS)
    finally:
        audio.unlink(missing_ok=True)
    return Prepared(peaks=found, storyboard=strip)


def _storyboard(gateways: TimelineMediaGateways, url: str, out_dir: Path) -> Storyboard | None:
    try:
        return gateways.storyboard(url, out_dir)
    except STORYBOARD_FAILURES:
        return None


def store(made: Prepared, folder: Path) -> None:
    """Keep ``made`` in ``folder``, replacing what an earlier preparation kept there."""
    folder.mkdir(parents=True, exist_ok=True)
    _write_json(folder / WAVEFORM_FILE, {"buckets": len(made.peaks), "peaks": _rounded(made)})
    if made.storyboard is None:
        (folder / THUMBNAILS_IMAGE).unlink(missing_ok=True)
        (folder / THUMBNAILS_LAYOUT).unlink(missing_ok=True)
        return
    strip = made.storyboard
    layout = {"width": strip.width, "height": strip.height, "times": strip.times}
    _write_json(folder / THUMBNAILS_LAYOUT, layout)
    shutil.copyfile(strip.image, folder / f"{THUMBNAILS_IMAGE}.new")
    os.replace(folder / f"{THUMBNAILS_IMAGE}.new", folder / THUMBNAILS_IMAGE)


def _rounded(made: Prepared) -> list[float]:
    return [round(peak, PEAK_DIGITS) for peak in made.peaks]


def _write_json(path: Path, content: dict[str, Any]) -> None:
    # Written aside and renamed, so a reader never sees half a file.
    partial = path.with_name(f"{path.name}.new")
    partial.write_text(json.dumps(content), encoding="utf-8")
    os.replace(partial, path)


def read_waveform(folder: Path) -> dict[str, Any] | None:
    """``{"buckets", "peaks"}`` kept in ``folder``, or ``None`` when there is none."""
    return _read_json(folder / WAVEFORM_FILE)


def read_thumbnails_layout(folder: Path) -> dict[str, Any] | None:
    """``{"width", "height", "times"}`` of the strip kept in ``folder``, or ``None``."""
    return _read_json(folder / THUMBNAILS_LAYOUT)


def thumbnails_image(folder: Path) -> Path | None:
    image = folder / THUMBNAILS_IMAGE
    return image if image.is_file() else None


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        content: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    return content


class LocalTimelineGateways:
    """The real outside world: YouTube through yt-dlp and ffmpeg."""

    def __init__(self, youtube: YouTube) -> None:
        self._youtube = youtube

    def storyboard(self, url: str, out_dir: Path) -> Storyboard | None:
        return build_storyboard(self._youtube.metadata(url), self._youtube.fetch, out_dir)

    def audio(self, url: str, output: Path) -> Path:
        return self._youtube.download_audio(url, output)

    def peaks(self, audio: Path, buckets: int) -> list[float]:
        return waveform.peaks(audio, buckets)


def default_gateways() -> TimelineMediaGateways:
    """The gateways of a real preparation; refused with ``network_error`` while the network
    is forbidden (ADR-0017)."""
    network.refuse_when_forbidden("o YouTube")
    return LocalTimelineGateways(YouTube())
