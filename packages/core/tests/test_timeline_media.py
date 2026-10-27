"""Preparing the media of the timeline through doubles of the outside world."""

from __future__ import annotations

from pathlib import Path

import pytest

from wordcut import timeline_media
from wordcut.timeline_media import PEAK_BUCKETS, prepare
from wordcut.timeline_media.storyboard import Storyboard
from wordcut.youtube import YouTubeError

URL = "https://youtu.be/Ab3_x-9QzLk"


class FakeTimelineGateways:
    """``TimelineMediaGateways`` double: writes small files where the real ones would."""

    def __init__(self, *, storyboard: str = "ok", audio: str = "ok") -> None:
        self._storyboard = storyboard
        self._audio = audio
        self.audio_files: list[Path] = []
        self.buckets: list[int] = []

    def storyboard(self, url: str, out_dir: Path) -> Storyboard | None:
        if self._storyboard == "missing":
            return None
        if self._storyboard == "fails":
            raise YouTubeError("O YouTube recusou o pedido.")
        out_dir.mkdir(parents=True, exist_ok=True)
        image = out_dir / "strip.jpg"
        image.write_bytes(b"jpeg")
        return Storyboard(image=image, width=160, height=90, times=[0.0, 50.0])

    def audio(self, url: str, output: Path) -> Path:
        if self._audio == "fails":
            raise YouTubeError("yt-dlp --cookies /segredos/youtube-cookies.txt falhou")
        output.write_bytes(b"audio")
        self.audio_files.append(output)
        return output

    def peaks(self, audio: Path, buckets: int) -> list[float]:
        assert audio.is_file()
        self.buckets.append(buckets)
        return [0.0, 0.5, 1.0]


def test_preparation_gives_the_strip_and_the_peaks_and_deletes_the_audio(tmp_path: Path) -> None:
    gateways = FakeTimelineGateways()

    made = prepare(gateways, tmp_path, URL)

    assert made.peaks == [0.0, 0.5, 1.0] and gateways.buckets == [PEAK_BUCKETS]
    assert made.storyboard is not None and made.storyboard.times == [0.0, 50.0]
    assert [audio.exists() for audio in gateways.audio_files] == [False]


@pytest.mark.parametrize("storyboard", ["missing", "fails"])
def test_live_without_a_storyboard_is_prepared_with_only_the_peaks(
    tmp_path: Path, storyboard: str
) -> None:
    made = prepare(FakeTimelineGateways(storyboard=storyboard), tmp_path, URL)

    assert (made.storyboard, made.peaks) == (None, [0.0, 0.5, 1.0])


def test_audio_that_fails_fails_the_preparation(tmp_path: Path) -> None:
    with pytest.raises(YouTubeError):
        prepare(FakeTimelineGateways(audio="fails"), tmp_path, URL)


def test_real_gateways_refuse_while_the_network_is_forbidden() -> None:
    with pytest.raises(Exception, match="test reached real timeline media"):
        timeline_media.default_gateways()
