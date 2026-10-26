import numpy as np

from wordcut.sync import find_clip_start

RATE = 1_000


def test_finds_clip_offset_in_noise() -> None:
    rng = np.random.default_rng(seed=7)
    recording = rng.standard_normal(20 * RATE).astype(np.float32)
    clip = recording[int(12.345 * RATE) : 15 * RATE].copy()

    assert abs(find_clip_start(recording, clip, RATE) - 12.345) < 1 / RATE
