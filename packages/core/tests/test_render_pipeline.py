from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path

import pytest

from wordcut import rendering
from wordcut.cuts.assembly import assemble
from wordcut.cuts.caption import DEFAULT_CAPTION, CaptionSettings
from wordcut.db.cuts import Segment
from wordcut.db.transcripts import WordRow
from wordcut.edit.timeline import Clip
from wordcut.rendering.options import RenderOptions
from wordcut.rendering.pipeline import Progress, render_cut
from wordcut.vertical.camera import CameraPath
from wordcut.vertical.captions import CaptionImage
from wordcut.vertical.detection import FrameDetections
from wordcut.vertical.render import Encoding

FPS = 30.0
SOURCE_WIDTH, SOURCE_HEIGHT = 320, 180
WORDS = tuple(
    WordRow(id=10 + position, position=position, text=text, start=start, end=end,
            score=None, estimated=False)
    for position, (text, start, end) in enumerate(
        [("Esther", 0.3, 0.7), ("orou.", 0.8, 1.2), ("Esther", 2.0, 2.4), ("jejuou.", 2.5, 3.0)]
    )
)  # fmt: skip


class FakeGateways:
    """``RenderGateways`` double: records what each step receives; the render writes a file."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.clips: list[Clip] = []
        self.smooth_joins: bool | None = None
        self.captions: list[CaptionImage] = []
        self.camera: CameraPath | None = None
        self.encoding: Encoding | None = None

    def geometry(self, media: Path) -> tuple[int, int, float]:
        return SOURCE_WIDTH, SOURCE_HEIGHT, FPS

    def energy(self, media: Path) -> Callable[[float], float]:
        return lambda t: 0.0

    def assemble(
        self, source: Path, clips: Sequence[Clip], output: Path, fps: float, *, smooth_joins: bool
    ) -> Path:
        self.calls.append("assemble")
        self.clips, self.smooth_joins = list(clips), smooth_joins
        output.write_bytes(b"montage")
        return output

    def detect(self, montage: Path, progress: Callable[[int, int], None]) -> list[FrameDetections]:
        self.calls.append("detect")
        progress(15, 30)
        progress(30, 30)
        return [FrameDetections(False, ())] * 30

    def render(
        self,
        montage: Path,
        camera: CameraPath,
        captions: Sequence[CaptionImage],
        fps: float,
        output: Path,
        encoding: Encoding,
    ) -> Path:
        self.calls.append("render")
        self.captions, self.encoding, self.camera = list(captions), encoding, camera
        output.write_bytes(b"video")
        return output


def export(
    tmp_path: Path,
    gateways: FakeGateways,
    segments: tuple[Segment, ...] = (Segment(10, 13),),
    *,
    fixes: dict[int, str] | None = None,
    caption: CaptionSettings = DEFAULT_CAPTION,
    options: RenderOptions | None = None,
    progress: Progress = lambda fraction, message: None,
) -> float:
    return render_cut(
        gateways,
        tmp_path / "sermon.mp4",
        WORDS,
        assemble(segments, WORDS, fixes or {}),
        caption,
        options or RenderOptions(),
        tmp_path / "work",
        tmp_path / "corte.mp4",
        progress,
    )


def caption_text(gateways: FakeGateways) -> str:
    return " ".join(line for image in gateways.captions for line in image.caption.lines)


def test_the_cut_is_assembled_then_detected_then_rendered_into_the_output(tmp_path: Path) -> None:
    gateways = FakeGateways()

    export(tmp_path, gateways)

    assert (gateways.calls, (tmp_path / "corte.mp4").read_bytes()) == (
        ["assemble", "detect", "render"],
        b"video",
    )


def test_the_captions_carry_the_fix_of_one_word_and_not_of_another_spelled_the_same(
    tmp_path: Path,
) -> None:
    gateways = FakeGateways()

    export(tmp_path, gateways, fixes={12: "Ester"})

    assert caption_text(gateways) == "Esther orou. Ester jejuou."


def test_with_the_caption_off_no_caption_reaches_the_render(tmp_path: Path) -> None:
    gateways = FakeGateways()

    export(tmp_path, gateways, caption=replace(DEFAULT_CAPTION, enabled=False))

    assert gateways.captions == []


@pytest.mark.parametrize(
    ("options", "smooth_joins", "encoding"),
    [
        (RenderOptions(), True, Encoding(1080, 1920, crf=18, normalize=True, fade=True)),
        (
            RenderOptions(
                smooth_joins=False,
                fade=False,
                normalize=False,
                resolution="720x1280",
                quality="small",
            ),
            False,
            Encoding(720, 1280, crf=26, normalize=False, fade=False),
        ),
    ],
    ids=["defaults", "changed"],
)
def test_the_options_reach_the_montage_and_the_encode(
    tmp_path: Path, options: RenderOptions, smooth_joins: bool, encoding: Encoding
) -> None:
    gateways = FakeGateways()

    export(tmp_path, gateways, options=options)

    assert (gateways.smooth_joins, gateways.encoding) == (smooth_joins, encoding)


def test_in_720_by_1280_the_captions_are_drawn_across_its_width_at_the_cut_s_height(
    tmp_path: Path,
) -> None:
    gateways = FakeGateways()
    high = replace(DEFAULT_CAPTION, position="top", offset=20)

    export(tmp_path, gateways, caption=high, options=RenderOptions(resolution="720x1280"))

    middles = {round(image.top + image.bgr.shape[0] / 2) for image in gateways.captions}
    widths = {image.bgr.shape[1] for image in gateways.captions}
    assert (widths, middles) == ({720}, {256})


def test_the_progress_goes_through_each_stage_in_order_always_forward(tmp_path: Path) -> None:
    heard: list[tuple[float, str]] = []

    export(tmp_path, FakeGateways(), progress=lambda *progress: heard.append(progress))

    stages = [message for index, (_, message) in enumerate(heard) if heard[index - 1][1] != message]
    fractions = [fraction for fraction, _ in heard]
    assert (stages, fractions == sorted(fractions)) == (
        ["montando", "detectando o pregador", "preparando legendas", "renderizando"],
        True,
    )


def test_the_camera_jumps_where_the_next_segment_starts_and_plays_in_the_cut_s_order(
    tmp_path: Path,
) -> None:
    gateways = FakeGateways()

    export(tmp_path, gateways, (Segment(12, 13), Segment(10, 11)))

    first_segment = sum(clip.duration for clip in gateways.clips if clip.segment == 0)
    assert (
        [word.text for clip in gateways.clips for word in clip.words],
        gateways.camera.scene_cuts if gateways.camera else None,
    ) == (["Esther", "jejuou.", "Esther", "orou."], [round(first_segment * FPS)])


class FailingRender(FakeGateways):
    """The encoder writes part of the file and then fails."""

    def render(
        self,
        montage: Path,
        camera: CameraPath,
        captions: Sequence[CaptionImage],
        fps: float,
        output: Path,
        encoding: Encoding,
    ) -> Path:
        output.write_bytes(b"part")
        raise RuntimeError("ffmpeg falhou")


def test_a_failed_render_raises_and_leaves_neither_the_output_nor_the_work_folder(
    tmp_path: Path,
) -> None:
    with pytest.raises(RuntimeError):
        export(tmp_path, FailingRender())

    assert sorted(path.name for path in tmp_path.iterdir()) == []


def test_a_test_that_reaches_the_real_rendering_gateways_fails() -> None:
    with pytest.raises(AssertionError, match="real rendering"):
        rendering.default_gateways()
