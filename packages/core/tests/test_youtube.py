import subprocess
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from wordcut import youtube
from wordcut.youtube import LiveInfo, YouTube, YouTubeError

FakeRun = Callable[..., subprocess.CompletedProcess[str]]


@pytest.fixture(autouse=True)
def no_real_yt_dlp(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        raise AssertionError("test reached the real yt-dlp")

    monkeypatch.setattr(youtube.subprocess, "run", refuse)


def youtube_with(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run: FakeRun) -> YouTube:
    """A ``YouTube`` with a cookies file whose ``yt-dlp`` calls go to ``run``."""
    cookies = tmp_path / "youtube-cookies.txt"
    cookies.write_text("# fictício\n")
    monkeypatch.setattr(youtube.subprocess, "run", run)
    return YouTube(cookies=cookies, ffmpeg_dir=None)


def failing_yt_dlp(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    raise subprocess.CalledProcessError(1, command, stderr="ERROR: Video unavailable")


def cookies_flag(command: list[str]) -> str:
    return command[command.index("--cookies") + 1]


def test_service_date_uses_church_timezone_not_utc() -> None:
    # 2026-10-18 19:04 in São Paulo is already the 19th in UTC
    info = LiveInfo.from_metadata(
        {
            "title": "Culto",
            "duration": 7718,
            "release_timestamp": 1792361083,
            "upload_date": "20261019",
            "live_status": "was_live",
        }
    )

    assert info.service_date == date(2026, 10, 18)
    assert info.is_finished


def test_live_in_progress_is_not_finished() -> None:
    info = LiveInfo.from_metadata(
        {"title": "Culto", "duration": 60, "timestamp": 1792361083, "live_status": "is_live"}
    )

    assert not info.is_finished


def test_missing_start_time_is_an_error() -> None:
    with pytest.raises(ValueError):
        LiveInfo.from_metadata({"title": "x", "duration": 1})


def test_section_args_limit_resolution_and_use_seconds() -> None:
    args = YouTube.section_args("URL", 2570.0, 5122.4, Path("out.mp4"))

    assert args[args.index("--download-sections") + 1] == "*2570.000-5122.400"
    assert "1080" in args[args.index("-f") + 1]
    assert args[-1] == "URL"


def test_missing_cookies_file_is_a_youtube_error_explained_without_its_path(
    tmp_path: Path,
) -> None:
    with pytest.raises(YouTubeError, match="cookies") as raised:
        YouTube(cookies=tmp_path / "none.txt").info("URL")

    assert str(tmp_path) not in str(raised.value)


def test_uses_bundled_ffmpeg_when_installed(tmp_path: Path) -> None:
    command = YouTube(cookies=tmp_path / "c.txt", ffmpeg_dir=tmp_path).base_command()

    assert command[command.index("--ffmpeg-location") + 1] == str(tmp_path)


def test_falls_back_to_system_ffmpeg(tmp_path: Path) -> None:
    command = YouTube(cookies=tmp_path / "c.txt", ffmpeg_dir=tmp_path / "missing").base_command()

    assert "--ffmpeg-location" not in command


def test_youtube_without_cookies_argument_uses_the_secrets_folder_set_after_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORDCUT_CONFIG", str(tmp_path / "segredos"))

    command = YouTube().base_command()

    assert cookies_flag(command) == str(tmp_path / "segredos" / "youtube-cookies.txt")


def test_failed_yt_dlp_call_is_a_youtube_error_that_hides_the_command_and_cookies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = youtube_with(tmp_path, monkeypatch, failing_yt_dlp)

    with pytest.raises(YouTubeError) as raised:
        source.info("https://youtu.be/Ab3_x-9QzLk")

    message = str(raised.value)
    assert ("yt-dlp" in message, str(tmp_path) in message) == (False, False)


def yt_dlp_printing(output: str) -> FakeRun:
    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout=output)

    return run


def test_unreadable_yt_dlp_answer_is_a_youtube_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = youtube_with(tmp_path, monkeypatch, yt_dlp_printing("<html>não é JSON"))

    with pytest.raises(YouTubeError):
        source.info("https://youtu.be/Ab3_x-9QzLk")


def test_video_without_start_time_is_a_youtube_error_that_says_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    answer = '{"title": "Culto", "duration": 60, "live_status": "was_live"}'
    source = youtube_with(tmp_path, monkeypatch, yt_dlp_printing(answer))

    with pytest.raises(YouTubeError, match="horário de início"):
        source.info("https://youtu.be/Ab3_x-9QzLk")


def test_live_in_progress_without_duration_has_unknown_duration() -> None:
    info = LiveInfo.from_metadata(
        {"title": "Culto", "timestamp": 1792361083, "live_status": "is_live"}
    )

    assert (info.duration, info.is_finished) == (None, False)
