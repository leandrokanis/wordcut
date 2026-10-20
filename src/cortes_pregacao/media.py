"""Thin wrappers around ffmpeg/ffprobe."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import numpy.typing as npt

FADE_SECONDS = 0.5


def extract_speech_audio(
    media: Path, output: Path, start: float = 0.0, duration: float | None = None
) -> Path:
    """Write audio as 16 kHz mono PCM, the format speech models expect."""
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}"]
    if duration is not None:
        command += ["-t", f"{duration:.3f}"]
    command += ["-i", str(media), "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le"]
    subprocess.run([*command, str(output)], check=True)
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
    return float(_probe_format(media)["duration"])


def start_time_seconds(media: Path) -> float:
    value = _probe_format(media).get("start_time")
    return float(value) if value not in (None, "N/A") else 0.0


def _probe_format(media: Path) -> dict[str, str]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-of", "json", str(media)],
        check=True,
        capture_output=True,
        text=True,
    )
    fmt: dict[str, str] = json.loads(result.stdout)["format"]
    return fmt


def cut_with_fades(source: Path, start: float, end: float, output: Path) -> Path:
    """Frame-accurate re-encoded cut with 0.5 s video/audio fades at both ends.

    Never overwrites ``output``.
    """
    if output.exists():
        raise FileExistsError(output)
    command = fade_cut_command(source, start, end, output, start_time_seconds(source))
    subprocess.run(command, check=True)
    return output


def fade_cut_command(
    source: Path, start: float, end: float, output: Path, source_start_time: float = 0.0
) -> list[str]:
    """ffmpeg arguments for :func:`cut_with_fades`.

    ``-ss``/``-to`` go after ``-i`` for frame accuracy. ffmpeg then filters
    *before* trimming, so fade times are absolute positions in the source
    (shifted by its container start time), not relative to the cut.
    """
    if end - start <= 2 * FADE_SECONDS:
        raise ValueError(f"trecho curto demais: {start:.3f} -> {end:.3f}")
    fade_in = start + source_start_time
    fade_out = end + source_start_time - FADE_SECONDS
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
        "-i", str(source), "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
        "-vf", _fade_in_out("fade", fade_in, fade_out),
        "-af", _fade_in_out("afade", fade_in, fade_out),
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
        str(output),
    ]  # fmt: skip


def _fade_in_out(filter_name: str, fade_in: float, fade_out: float) -> str:
    return (
        f"{filter_name}=t=in:st={fade_in:.3f}:d={FADE_SECONDS},"
        f"{filter_name}=t=out:st={fade_out:.3f}:d={FADE_SECONDS}"
    )
