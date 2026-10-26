"""Export of a cut: the 9:16 video made from its current state (docs/cli.md §8.7).

``pipeline.render_cut`` does the work through ``RenderGateways``, the heavy outside world
(ffprobe, ffmpeg and OpenCV on the sermon's video); ``default_gateways`` builds the real
ones, and tests hand the pipeline doubles instead (ADR-0018).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol

from wordcut.edit import assemble as montage
from wordcut.edit.energy import EnergyProfile
from wordcut.edit.timeline import Clip, Energy
from wordcut.media import video_geometry
from wordcut.vertical.camera import CameraPath
from wordcut.vertical.captions import CaptionImage
from wordcut.vertical.detection import FrameDetections, detect_frames
from wordcut.vertical.render import Encoding, render_vertical

FramesDone = Callable[[int, int], None]
"""Called with (frames done, total frames)."""


class RenderGateways(Protocol):
    def geometry(self, media: Path) -> tuple[int, int, float]:
        """Width and height in pixels and frame rate of the video of ``media``."""

    def energy(self, media: Path) -> Energy:
        """Loudness of the audio of ``media`` around each of its times."""

    def assemble(
        self, source: Path, clips: Sequence[Clip], output: Path, fps: float, *, smooth_joins: bool
    ) -> Path:
        """The horizontal montage of the ``clips`` of ``source``, at ``fps``."""

    def detect(self, montage: Path, progress: FramesDone) -> list[FrameDetections]:
        """The people and scene cuts of each frame of ``montage``."""

    def render(
        self,
        montage: Path,
        camera: CameraPath,
        captions: Sequence[CaptionImage],
        fps: float,
        output: Path,
        encoding: Encoding,
    ) -> Path:
        """The vertical video of ``montage``, framed by ``camera``, with ``captions``."""


class LocalGateways:
    """The real outside world: ffprobe, ffmpeg and OpenCV."""

    def geometry(self, media: Path) -> tuple[int, int, float]:
        return video_geometry(media)

    def energy(self, media: Path) -> Energy:
        return EnergyProfile.from_media(media)

    def assemble(
        self, source: Path, clips: Sequence[Clip], output: Path, fps: float, *, smooth_joins: bool
    ) -> Path:
        return montage.assemble(source, clips, output, fps, smooth_joins=smooth_joins)

    def detect(self, montage: Path, progress: FramesDone) -> list[FrameDetections]:
        return detect_frames(montage, progress=progress)

    def render(
        self,
        montage: Path,
        camera: CameraPath,
        captions: Sequence[CaptionImage],
        fps: float,
        output: Path,
        encoding: Encoding,
    ) -> Path:
        return render_vertical(montage, camera, captions, fps, output, encoding)


def default_gateways() -> RenderGateways:
    """The gateways of a real export."""
    return LocalGateways()
