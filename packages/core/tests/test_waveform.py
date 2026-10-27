"""The peaks of the waveform: ffmpeg on synthetic audio made here, nothing from YouTube."""

import shutil
import subprocess
from pathlib import Path

import pytest

from wordcut.timeline_media.waveform import peaks

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="requires ffmpeg")

SINE = "sin(2*PI*440*t)"


def synthetic(folder: Path, expression: str, seconds: float) -> Path:
    """An audio file of ``seconds`` whose samples are ``expression`` of ``t`` (ffmpeg aevalsrc)."""
    audio = folder / "audio.wav"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"aevalsrc='{expression}':s=8000:d={seconds}", str(audio)],
        check=True,
    )  # fmt: skip
    return audio


def test_peaks_are_as_many_as_the_buckets_asked_and_between_zero_and_one(tmp_path: Path) -> None:
    audio = synthetic(tmp_path, f"0.5*{SINE}", 10)

    found = peaks(audio, 37)

    assert len(found) == 37 and all(0 <= peak <= 1 for peak in found)


def test_silence_has_zero_peaks(tmp_path: Path) -> None:
    audio = synthetic(tmp_path, "0", 5)

    assert peaks(audio, 20) == [0.0] * 20


def test_quiet_sine_of_fixed_loudness_is_scaled_to_full_peaks(tmp_path: Path) -> None:
    audio = synthetic(tmp_path, f"0.25*{SINE}", 10)

    assert all(peak == pytest.approx(1, abs=0.02) for peak in peaks(audio, 10))


def test_a_short_burst_marks_its_bucket_alone(tmp_path: Path) -> None:
    """A 50 ms burst twice as loud as the steady sine, inside the fourth of ten buckets."""
    burst = f"if(between(t,3.4,3.45),2,1)*0.4*{SINE}"
    audio = synthetic(tmp_path, burst, 10)

    found = peaks(audio, 10)

    assert [round(peak, 1) for peak in found] == [0.5, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]


def test_sound_in_the_middle_peaks_only_in_the_middle_buckets(tmp_path: Path) -> None:
    audio = synthetic(tmp_path, f"between(t,4,6)*0.5*{SINE}", 10)

    found = peaks(audio, 5)

    assert [round(peak) for peak in found] == [0, 0, 1, 0, 0]


def test_audio_shorter_than_the_buckets_still_gives_every_bucket(tmp_path: Path) -> None:
    audio = synthetic(tmp_path, f"0.5*{SINE}", 0.002)

    found = peaks(audio, 4000)

    assert len(found) == 4000 and max(found) == 1
