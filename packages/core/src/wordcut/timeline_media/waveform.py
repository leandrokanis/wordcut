"""The peaks of a waveform, read from any audio ffmpeg decodes."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import numpy.typing as npt

SAMPLE_RATE = 8000
# Samples are read and reduced this many at a time, so a two-hour live never sits in memory.
CHUNK_SAMPLES = SAMPLE_RATE * 60
# A block is the smallest stretch of audio a peak can stand for: 10 ms.
BLOCK_SAMPLES = SAMPLE_RATE // 100
SAMPLE_BYTES = 2
FULL_SCALE = 32768.0


def peaks(audio: Path, buckets: int) -> list[float]:
    """The loudest sample of each of ``buckets`` equal stretches of ``audio``, in order,
    scaled so that the loudest of all is 1; silence gives zeros."""
    blocks = _block_peaks(audio)
    if blocks.size == 0:
        return [0.0] * buckets
    edges = (np.arange(buckets) * blocks.size) // buckets
    # reduceat gives the block at an edge when the next edge does not move past it.
    bucketed = np.maximum.reduceat(blocks, edges)
    loudest = float(bucketed.max())
    if loudest == 0:
        return [0.0] * buckets
    return [float(value) for value in bucketed / loudest]


def _block_peaks(audio: Path) -> npt.NDArray[np.float32]:
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(audio),
        "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-",
    ]  # fmt: skip
    found: list[npt.NDArray[np.float32]] = []
    with subprocess.Popen(command, stdout=subprocess.PIPE) as decoder:
        assert decoder.stdout is not None
        while chunk := decoder.stdout.read(CHUNK_SAMPLES * SAMPLE_BYTES):
            found.append(_chunk_peaks(chunk))
    if decoder.returncode != 0:
        raise subprocess.CalledProcessError(decoder.returncode, command[0])
    return np.concatenate(found) if found else np.zeros(0, dtype=np.float32)


def _chunk_peaks(chunk: bytes) -> npt.NDArray[np.float32]:
    samples = np.abs(np.frombuffer(chunk, dtype=np.int16).astype(np.float32)) / FULL_SCALE
    starts = np.arange(0, samples.size, BLOCK_SAMPLES)
    reduced: npt.NDArray[np.float32] = np.maximum.reduceat(samples, starts)
    return reduced
