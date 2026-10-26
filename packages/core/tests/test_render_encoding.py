from pathlib import Path

from wordcut.edit.assemble import montage_command
from wordcut.edit.timeline import Clip
from wordcut.vertical.render import Encoding, encoder_command

CLIPS = [Clip(10.0, 12.0, (), 0), Clip(30.5, 31.0, (), 1)]


def filter_graph(command: list[str]) -> str:
    return command[command.index("-filter_complex") + 1]


def test_joins_without_smoothing_have_no_audio_fade() -> None:
    command = montage_command(Path("src.mp4"), CLIPS, Path("out.mov"), 30.0, smooth_joins=False)

    assert "afade" not in filter_graph(command)


def test_smoothed_joins_fade_the_audio_out_and_in_at_every_clip() -> None:
    command = montage_command(Path("src.mp4"), CLIPS, Path("out.mov"), 30.0, smooth_joins=True)

    assert filter_graph(command).count("afade=") == 2 * len(CLIPS)


def encoded(encoding: Encoding, duration: float = 30.0) -> list[str]:
    return encoder_command(Path("montage.mov"), 30.0, duration, Path("out.mp4"), encoding)


def option(command: list[str], name: str) -> str:
    return command[command.index(name) + 1]


def test_the_encoder_takes_frames_in_the_chosen_resolution() -> None:
    assert option(encoded(Encoding(width=720, height=1280)), "-s") == "720x1280"


def test_a_smaller_file_is_encoded_with_a_higher_crf() -> None:
    assert option(encoded(Encoding(crf=26)), "-crf") == "26"


def test_without_normalization_the_audio_is_only_resampled() -> None:
    assert option(encoded(Encoding(normalize=False)), "-af") == "aresample=48000"


def test_normalization_brings_the_audio_to_minus_14_lufs() -> None:
    assert "loudnorm=I=-14" in option(encoded(Encoding(normalize=True)), "-af")


def test_a_fade_takes_half_a_second_in_and_out_of_video_and_audio() -> None:
    command = encoded(Encoding(fade=True), duration=30.0)

    fades = ["fade=t=in:st=0.000:d=0.500", "fade=t=out:st=29.500:d=0.500"]
    assert (option(command, "-vf"), option(command, "-af")) == (
        f"{fades[0]},{fades[1]},format=yuv420p",
        f"loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,a{fades[0]},a{fades[1]}",
    )


def test_a_cut_shorter_than_both_fades_fades_for_half_its_length_each_way() -> None:
    command = encoded(Encoding(fade=True), duration=0.6)

    assert option(command, "-vf") == (
        "fade=t=in:st=0.000:d=0.300,fade=t=out:st=0.300:d=0.300,format=yuv420p"
    )
