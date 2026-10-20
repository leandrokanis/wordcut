from pathlib import Path

import pytest

from cortes_pregacao.media import fade_cut_command


def option(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def test_fade_times_are_absolute_in_source() -> None:
    command = fade_cut_command(Path("in.mp4"), 30.064, 2522.364, Path("out.mp4"))

    assert option(command, "-ss") == "30.064"
    assert option(command, "-to") == "2522.364"
    assert option(command, "-vf") == "fade=t=in:st=30.064:d=0.5,fade=t=out:st=2521.864:d=0.5"
    assert option(command, "-af") == "afade=t=in:st=30.064:d=0.5,afade=t=out:st=2521.864:d=0.5"


def test_fades_follow_container_start_time() -> None:
    command = fade_cut_command(Path("in.mp4"), 10.0, 20.0, Path("out.mp4"), source_start_time=1.4)

    assert option(command, "-vf").startswith("fade=t=in:st=11.400")


def test_seek_comes_after_input_for_frame_accuracy() -> None:
    command = fade_cut_command(Path("in.mp4"), 10.0, 20.0, Path("out.mp4"))

    assert command.index("-i") < command.index("-ss")
    assert "-n" in command  # never overwrite


def test_rejects_cut_shorter_than_fades() -> None:
    with pytest.raises(ValueError):
        fade_cut_command(Path("in.mp4"), 10.0, 10.9, Path("out.mp4"))
