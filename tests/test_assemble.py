from pathlib import Path

import numpy as np
import pytest

from cortes_pregacao.edit.assemble import montage_command
from cortes_pregacao.edit.energy import EnergyProfile
from cortes_pregacao.edit.timeline import Clip


def test_one_seeked_input_per_clip_and_concat() -> None:
    clips = [Clip(10.0, 12.0, (), 0), Clip(30.5, 31.0, (), 1)]

    command = montage_command(Path("src.mp4"), clips, Path("out.mov"))

    assert command.count("-i") == 2
    assert command[command.index("-ss") + 1] == "10.000000"
    graph = command[command.index("-filter_complex") + 1]
    assert "concat=n=2:v=1:a=1" in graph
    assert "afade=t=out:st=0.485000:d=0.015" in graph


def test_empty_timeline_is_rejected() -> None:
    with pytest.raises(ValueError):
        montage_command(Path("src.mp4"), [], Path("out.mov"))


def test_energy_profile_finds_silence() -> None:
    rate = 8_000
    loud = np.ones(rate, dtype=np.float32) * 0.5
    silence = np.zeros(rate, dtype=np.float32)
    profile = EnergyProfile.from_samples(np.concatenate([loud, silence, loud]), rate)

    assert profile(1.5) == 0.0
    assert profile(0.5) == pytest.approx(0.5)
