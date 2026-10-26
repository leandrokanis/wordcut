"""Render the vertical short: crop + scale per frame, captions, final encode."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from wordcut.vertical.camera import ASPECT, CameraPath
from wordcut.vertical.captions import CaptionImage
from wordcut.vertical.detection import Frame

OUTPUT_WIDTH, OUTPUT_HEIGHT = 1080, 1920
LOUDNESS = "loudnorm=I=-14:TP=-1.5:LRA=11"  # social media loudness
RESAMPLE = "aresample=48000"  # loudnorm works at 192 kHz; back to the usual rate
FADE_S = 0.5


@dataclass(frozen=True)
class Encoding:
    """How the short is encoded: its frame size in pixels, the x264 quality (CRF, lower is
    better and bigger), the audio brought to social media loudness, and a fade in at the
    start and out at the end of video and audio."""

    width: int = OUTPUT_WIDTH
    height: int = OUTPUT_HEIGHT
    crf: int = 18
    normalize: bool = True
    fade: bool = False


DEFAULT_ENCODING = Encoding()


def render_vertical(
    montage: Path,
    camera: CameraPath,
    captions: Sequence[CaptionImage],
    fps: float,
    output: Path,
    encoding: Encoding = DEFAULT_ENCODING,
) -> Path:
    if output.exists():
        raise FileExistsError(output)
    frame_count = len(camera.centres)
    encoder = subprocess.Popen(
        encoder_command(montage, fps, frame_count / fps, output, encoding), stdin=subprocess.PIPE
    )
    assert encoder.stdin is not None
    capture = cv2.VideoCapture(str(montage))
    try:
        for index in range(frame_count):
            ok, frame = capture.read()
            if not ok:
                break
            image = _reframe(frame, float(camera.centres[index]), encoding)
            _overlay(image, captions, index / fps)
            encoder.stdin.write(image.tobytes())
    finally:
        capture.release()
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError("ffmpeg falhou ao codificar o corte vertical")
    return output


def _reframe(frame: Frame, centre_x: float, encoding: Encoding) -> Frame:
    """Subpixel crop of the 9:16 window centred at ``centre_x``, scaled to output size."""
    height = frame.shape[0]
    scale = encoding.height / height
    window = height * ASPECT
    transform = np.array(
        [[scale, 0, -(centre_x - window / 2) * scale], [0, scale, 0]], dtype=np.float32
    )
    return cv2.warpAffine(
        frame, transform, (encoding.width, encoding.height),
        flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE,
    )  # fmt: skip


def _overlay(image: Frame, captions: Sequence[CaptionImage], t: float) -> None:
    for caption in captions:
        if caption.caption.start <= t < caption.caption.end:
            rows = slice(caption.top, caption.top + caption.bgr.shape[0])
            base = image[rows].astype(np.float32)
            blended = caption.bgr * caption.alpha + base * (1 - caption.alpha)
            image[rows] = blended.astype(np.uint8)


def encoder_command(
    montage: Path, fps: float, duration: float, output: Path, encoding: Encoding
) -> list[str]:
    """ffmpeg arguments that encode raw BGR frames from stdin with the montage's audio."""
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{encoding.width}x{encoding.height}",
        "-r", f"{fps}", "-i", "-",
        "-i", str(montage), "-map", "0:v", "-map", "1:a",
        "-vf", _video_filter(encoding, duration), "-af", _audio_filter(encoding, duration),
        "-c:v", "libx264", "-crf", str(encoding.crf), "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-t", f"{duration:.3f}", str(output),
    ]  # fmt: skip


def _video_filter(encoding: Encoding, duration: float) -> str:
    return ",".join([*_fades("fade", encoding, duration), "format=yuv420p"])


def _audio_filter(encoding: Encoding, duration: float) -> str:
    levels = [LOUDNESS, RESAMPLE] if encoding.normalize else [RESAMPLE]
    return ",".join([*levels, *_fades("afade", encoding, duration)])


def _fades(name: str, encoding: Encoding, duration: float) -> list[str]:
    if not encoding.fade:
        return []
    # A short cut fades for half its length each way, so the fades never overlap.
    length = min(FADE_S, duration / 2)
    return [
        f"{name}=t=in:st=0.000:d={length:.3f}",
        f"{name}=t=out:st={duration - length:.3f}:d={length:.3f}",
    ]
