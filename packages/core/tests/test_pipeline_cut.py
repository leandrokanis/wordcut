"""The pipeline with the real cut: ffmpeg on a synthetic 3 s clip, nothing from YouTube."""

import shutil
import subprocess
from pathlib import Path

import pytest

from wordcut.media import duration_seconds, video_geometry
from wordcut.processing import LocalGateways, pipeline
from wordcut.transcript import Transcript, Word
from wordcut.youtube import YouTube

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="requires ffmpeg")

CLIP_SECONDS = 3
WIDTH, HEIGHT = 320, 180
FRAME_RATE = 30
# The borders; the window starts 50 s before them and the clip plays from the first one.
LIVE_START, LIVE_END = 100.0, 200.0
SECTION_WORDS = (Word("Irmãos", 0.5, 0.8), Word("Amém.", 1.2, 1.4))


class FakeTranscriber:
    def transcribe(self, audio: Path, output: Path) -> None:
        Transcript(words=SECTION_WORDS, language="pt", model="fake").save(output)


class SyntheticSection(LocalGateways):
    """Real duration and cut; the section is a synthetic clip that starts at ``LIVE_START``."""

    def download_section(self, url: str, start: float, end: float, output: Path) -> Path:
        subprocess.run(
            ["ffmpeg", "-loglevel", "error",
             "-f", "lavfi", "-i", f"testsrc2=size={WIDTH}x{HEIGHT}:rate={FRAME_RATE}",
             "-f", "lavfi", "-i", "sine=frequency=440", "-t", str(CLIP_SECONDS),
             "-c:v", "libx264", "-c:a", "aac", str(output)],
            check=True,
        )  # fmt: skip
        return output

    def download_audio_window(self, url: str, start: float, end: float, output: Path) -> Path:
        output.touch()
        return output

    def locate(self, recording: Path, clip: Path, expected_start: float, search: float) -> float:
        return 50.0

    def transcribe(self, media: Path, workdir: Path) -> Transcript:
        return Transcript(words=SECTION_WORDS, language="pt", model="fake")


def test_the_cut_sermon_lasts_from_its_start_to_its_end_in_the_source_geometry_with_audio(
    tmp_path: Path,
) -> None:
    gateways = SyntheticSection(YouTube(cookies=tmp_path / "sem-cookies.txt"), FakeTranscriber())

    processed = pipeline.process(
        gateways, tmp_path, "https://youtu.be/Ab3_x-9QzLk", LIVE_START, LIVE_END, lambda *_: None
    )

    assert (
        duration_seconds(processed.video),
        video_geometry(processed.video)[:2],
        has_audio(processed.video),
    ) == (
        pytest.approx(processed.sermon_end - processed.sermon_start, abs=1 / FRAME_RATE),
        (WIDTH, HEIGHT),
        True,
    )


def has_audio(media: Path) -> bool:
    streams = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
         "-of", "csv=p=0", str(media)],
        check=True, capture_output=True, text=True,
    ).stdout  # fmt: skip
    return bool(streams.strip())
