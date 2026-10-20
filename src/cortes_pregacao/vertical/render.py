"""Render the 1080x1920 short: crop + scale per frame, captions, final encode."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import cv2
import numpy as np

from cortes_pregacao.vertical.camera import ASPECT, CameraPath
from cortes_pregacao.vertical.captions import CaptionImage
from cortes_pregacao.vertical.detection import Frame

OUTPUT_WIDTH, OUTPUT_HEIGHT = 1080, 1920
LOUDNESS = "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000"  # social media loudness


def render_vertical(
    montage: Path,
    camera: CameraPath,
    captions: Sequence[CaptionImage],
    fps: float,
    output: Path,
) -> Path:
    if output.exists():
        raise FileExistsError(output)
    frame_count = len(camera.centres)
    encoder = subprocess.Popen(
        _encoder_command(montage, fps, frame_count / fps, output), stdin=subprocess.PIPE
    )
    assert encoder.stdin is not None
    capture = cv2.VideoCapture(str(montage))
    try:
        for index in range(frame_count):
            ok, frame = capture.read()
            if not ok:
                break
            image = _reframe(frame, float(camera.centres[index]))
            _overlay(image, captions, index / fps)
            encoder.stdin.write(image.tobytes())
    finally:
        capture.release()
        encoder.stdin.close()
    if encoder.wait() != 0:
        raise RuntimeError("ffmpeg falhou ao codificar o corte vertical")
    return output


def _reframe(frame: Frame, centre_x: float) -> Frame:
    """Subpixel crop of the 9:16 window centred at ``centre_x``, scaled to output size."""
    height = frame.shape[0]
    scale = OUTPUT_HEIGHT / height
    window = height * ASPECT
    transform = np.array(
        [[scale, 0, -(centre_x - window / 2) * scale], [0, scale, 0]], dtype=np.float32
    )
    return cv2.warpAffine(
        frame, transform, (OUTPUT_WIDTH, OUTPUT_HEIGHT),
        flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE,
    )  # fmt: skip


def _overlay(image: Frame, captions: Sequence[CaptionImage], t: float) -> None:
    for caption in captions:
        if caption.caption.start <= t < caption.caption.end:
            rows = slice(caption.top, caption.top + caption.bgr.shape[0])
            base = image[rows].astype(np.float32)
            blended = caption.bgr * caption.alpha + base * (1 - caption.alpha)
            image[rows] = blended.astype(np.uint8)


def _encoder_command(montage: Path, fps: float, duration: float, output: Path) -> list[str]:
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OUTPUT_WIDTH}x{OUTPUT_HEIGHT}",
        "-r", f"{fps}", "-i", "-",
        "-i", str(montage), "-map", "0:v", "-map", "1:a",
        "-vf", "format=yuv420p", "-af", LOUDNESS,
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        "-t", f"{duration:.3f}", str(output),
    ]  # fmt: skip
