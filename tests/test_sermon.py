import shutil
import subprocess
from pathlib import Path

import pytest

from cortes_pregacao.sermon import RANGE_MARGIN_S, transcribe_live
from cortes_pregacao.sermon_folder import SermonFolder
from cortes_pregacao.transcript import Transcript, Word

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="requires ffmpeg")


class FakeYouTube:
    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        self.downloads = 0

    def download_audio(self, url: str, output: Path) -> Path:
        self.downloads += 1
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
             f"sine=frequency=440:duration={self.seconds}", str(output)],
            check=True,
        )  # fmt: skip
        return output


class FakeTranscriber:
    """Hears one word one second into whatever audio it is given."""

    def transcribe(self, audio: Path, output: Path) -> None:
        Transcript((Word("palavra", 1.0, 1.5),), language="pt", model="fake").save(output)


def test_range_transcript_is_shifted_to_live_time(tmp_path: Path) -> None:
    youtube = FakeYouTube(seconds=200)
    folder = SermonFolder(tmp_path / "pregação")

    transcript = transcribe_live(
        youtube,  # type: ignore[arg-type]
        FakeTranscriber(),
        "URL",
        folder,
        approx_start=100.0,
        approx_end=120.0,
    )

    expected = 100.0 - RANGE_MARGIN_S + 1.0
    assert transcript.words[0].start == pytest.approx(expected)
    assert Transcript.load(folder.live_words) == transcript


def test_live_audio_is_downloaded_once(tmp_path: Path) -> None:
    youtube = FakeYouTube(seconds=5)
    folder = SermonFolder(tmp_path / "pregação")

    for _ in range(2):
        transcribe_live(youtube, FakeTranscriber(), "URL", folder)  # type: ignore[arg-type]

    assert youtube.downloads == 1
