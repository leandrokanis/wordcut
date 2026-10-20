"""Locate a clip inside a longer recording by audio cross-correlation.

YouTube section downloads start at a keyframe near the requested time, not at
the exact second, so times computed from the request can be off by seconds.
"""

from __future__ import annotations

import numpy as np
import numpy.typing as npt

from cortes_pregacao.media import read_audio

SYNC_RATE = 4_000  # Hz; plenty for speech envelopes, keeps correlation cheap
PROBE_SECONDS = 30.0


def find_clip_start(
    recording: npt.NDArray[np.float32],
    clip: npt.NDArray[np.float32],
    rate: int,
) -> float:
    """Seconds into ``recording`` where ``clip`` best matches."""
    if len(clip) > len(recording):
        raise ValueError("clip is longer than the searched recording")
    size = 1 << (len(recording) + len(clip)).bit_length()
    spectrum = np.fft.rfft(recording, size) * np.conj(np.fft.rfft(clip, size))
    correlation = np.fft.irfft(spectrum, size)[: len(recording) - len(clip) + 1]
    return float(np.argmax(correlation)) / rate


def locate_clip(recording_path: str, clip_path: str, expected_start: float, search: float) -> float:
    """Start of ``clip_path`` within ``recording_path``, searched around ``expected_start``."""
    window_start = max(0.0, expected_start - search)
    recording = read_audio(
        recording_path, SYNC_RATE, start=window_start, duration=2 * search + PROBE_SECONDS
    )
    clip = read_audio(clip_path, SYNC_RATE, start=0.0, duration=PROBE_SECONDS)
    return window_start + find_clip_start(recording, clip, SYNC_RATE)
