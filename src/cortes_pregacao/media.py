"""Thin wrappers around ffmpeg/ffprobe."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import numpy.typing as npt


def extract_speech_audio(video: Path, output: Path) -> Path:
    """Write the audio track as 16 kHz mono PCM, the format speech models expect."""
    subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(video),
            "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            str(output),
        ],
        check=True,
    )  # fmt: skip
    return output


def read_audio(
    media: Path | str, rate: int, start: float = 0.0, duration: float | None = None
) -> npt.NDArray[np.float32]:
    """Decode mono audio as float32 samples in [-1, 1]."""
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}"]
    if duration is not None:
        command += ["-t", f"{duration:.3f}"]
    command += ["-i", str(media), "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "-"]
    raw = subprocess.run(command, check=True, capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0


def duration_seconds(media: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(media)],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])
