"""The export with the real montage and encode: ffmpeg on a synthetic 2 s clip in 720x1280.

People detection is a double; nothing else of the export is.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from wordcut.cuts.assembly import assemble
from wordcut.cuts.caption import DEFAULT_CAPTION
from wordcut.db.cuts import Segment
from wordcut.db.transcripts import WordRow
from wordcut.media import duration_seconds, video_geometry
from wordcut.rendering import FramesDone, LocalGateways
from wordcut.rendering.options import RenderOptions
from wordcut.rendering.pipeline import render_cut
from wordcut.vertical.detection import FrameDetections

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="requires ffmpeg")

CLIP_SECONDS = 2
WIDTH, HEIGHT = 320, 180
FRAME_RATE = 30
# AAC frames hold 1024 samples, so the audio may outlast the video by about one of them.
AAC_SLACK_S = 1024 / 48_000
WORDS = tuple(
    WordRow(id=1 + position, position=position, text=text, start=start, end=end,
            score=None, estimated=False)
    for position, (text, start, end) in enumerate(
        [("Irmãos,", 0.2, 0.6), ("graça", 0.7, 1.0), ("e", 1.05, 1.1), ("paz.", 1.15, 1.6)]
    )
)  # fmt: skip


class NobodyOnStage(LocalGateways):
    """Real ffprobe and ffmpeg; detection finds no one, in every frame of the montage."""

    def detect(self, montage: Path, progress: FramesDone) -> list[FrameDetections]:
        frames = round(duration_seconds(montage) * video_geometry(montage)[2])
        return [FrameDetections(False, ())] * frames


def synthetic_sermon(folder: Path) -> Path:
    video = folder / "sermon.mp4"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error",
         "-f", "lavfi", "-i", f"testsrc2=size={WIDTH}x{HEIGHT}:rate={FRAME_RATE}",
         "-f", "lavfi", "-i", "sine=frequency=440", "-t", str(CLIP_SECONDS),
         "-c:v", "libx264", "-c:a", "aac", str(video)],
        check=True,
    )  # fmt: skip
    return video


def has_audio(media: Path) -> bool:
    streams = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
         "-of", "csv=p=0", str(media)],
        check=True, capture_output=True, text=True,
    ).stdout  # fmt: skip
    return bool(streams.strip())


def test_the_export_in_720_by_1280_has_that_size_audio_and_the_timeline_s_duration(
    tmp_path: Path,
) -> None:
    output = tmp_path / "corte.mp4"

    duration = render_cut(
        NobodyOnStage(),
        synthetic_sermon(tmp_path),
        WORDS,
        assemble((Segment(1, 4),), WORDS, {}),
        DEFAULT_CAPTION,
        RenderOptions(resolution="720x1280", quality="small"),
        tmp_path / "work",
        output,
        lambda fraction, message: None,
    )

    assert (video_geometry(output)[:2], has_audio(output), duration_seconds(output)) == (
        (720, 1280),
        True,
        pytest.approx(duration, abs=1 / FRAME_RATE + AAC_SLACK_S),
    )
