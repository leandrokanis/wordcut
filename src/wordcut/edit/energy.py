"""Short-time loudness of a recording, for placing cuts in silence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt

from wordcut.media import read_audio

SAMPLE_RATE = 8_000
WINDOW_S = 0.010


@dataclass(frozen=True)
class EnergyProfile:
    """RMS level per 10 ms window."""

    rms: npt.NDArray[np.float32]

    @classmethod
    def from_samples(cls, samples: npt.NDArray[np.float32], rate: int) -> EnergyProfile:
        window = max(1, round(rate * WINDOW_S))
        usable = len(samples) - len(samples) % window
        frames = samples[:usable].reshape(-1, window)
        return cls(np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1)).astype(np.float32))

    @classmethod
    def from_media(cls, media: Path) -> EnergyProfile:
        return cls.from_samples(read_audio(media, SAMPLE_RATE), SAMPLE_RATE)

    def __call__(self, t: float) -> float:
        """Level around ``t``: mean of the windows touching ``t`` ± 10 ms."""
        index = int(t / WINDOW_S)
        window = self.rms[max(0, index - 1) : index + 2]
        return float(window.mean()) if len(window) else 0.0
