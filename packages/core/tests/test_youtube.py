import json
import subprocess
import sys
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

    real_popen = subprocess.Popen

    def only_fakes(command: list[str], **kwargs: Any) -> subprocess.Popen[str]:
        if command[0] == "yt-dlp":
            raise AssertionError("test reached the real yt-dlp")
        return real_popen(command, **kwargs)

    monkeypatch.setattr(youtube.subprocess, "run", refuse)
    monkeypatch.setattr(youtube.subprocess, "Popen", only_fakes)


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


def test_audio_window_args_ask_only_the_audio_of_the_section_in_seconds() -> None:
    args = YouTube.audio_window_args("URL", 950.0, 1040.5, Path("janela.m4a"))

    assert (
        args[args.index("-f") + 1],
        args[args.index("--download-sections") + 1],
        args[args.index("-o") + 1],
        args[-1],
    ) == ("ba[ext=m4a]/ba", "*950.000-1040.500", "janela.m4a", "URL")


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


def fake_yt_dlp(tmp_path: Path, *lines: str, exit_code: int = 0) -> YouTube:
    """A ``YouTube`` whose yt-dlp is a Python process printing ``lines`` and exiting so."""
    cookies = tmp_path / "youtube-cookies.txt"
    cookies.write_text("# fictício\n")
    script = f"import sys\nfor line in {list(lines)!r}:\n    print(line)\nsys.exit({exit_code})"
    return YouTube(cookies=cookies, ffmpeg_dir=None, program=(sys.executable, "-c", script))


def window_progress(source: YouTube, tmp_path: Path) -> list[float]:
    heard: list[float] = []
    source.download_audio_window(
        "https://youtu.be/Ab3_x-9QzLk", 950.0, 1040.0, tmp_path / "w.m4a", on_progress=heard.append
    )
    return heard


def test_downloaded_media_time_over_the_section_length_is_the_download_progress(
    tmp_path: Path,
) -> None:
    source = fake_yt_dlp(tmp_path, "out_time_us=22500000", "out_time_us=45000000")

    assert window_progress(source, tmp_path) == [0.25, 0.5]


def test_downloaded_bytes_over_the_total_or_its_estimate_is_the_download_progress(
    tmp_path: Path,
) -> None:
    source = fake_yt_dlp(tmp_path, "wordcut-progress 30 NA 120", "wordcut-progress 60 120 NA")

    assert window_progress(source, tmp_path) == [0.25, 0.5]


def test_downloads_ask_yt_dlp_and_its_ffmpeg_to_print_progress_line_by_line(
    tmp_path: Path,
) -> None:
    argv = tmp_path / "argv.json"
    cookies = tmp_path / "youtube-cookies.txt"
    cookies.write_text("# fictício\n")
    script = f"import json, sys\nopen({str(argv)!r}, 'w').write(json.dumps(sys.argv[1:]))"
    source = YouTube(cookies=cookies, ffmpeg_dir=None, program=(sys.executable, "-c", script))

    window_progress(source, tmp_path)

    command = json.loads(argv.read_text())
    template = command[command.index("--progress-template") + 1]
    assert (
        {"--quiet", "--newline", "--progress"} <= set(command),
        template.startswith("download:"),
        command[command.index("--downloader-args") + 1],
    ) == (True, True, "ffmpeg_o:-progress pipe:1")


def test_lines_that_are_not_progress_and_bytes_without_total_are_ignored(
    tmp_path: Path,
) -> None:
    source = fake_yt_dlp(
        tmp_path,
        "[download] Destination: w.m4a",
        "out_time_us=N/A",
        "wordcut-progress 10 NA NA",
        "progress=continue",
        "out_time_us=45000000",
    )

    assert window_progress(source, tmp_path) == [0.5]


def section_progress(source: YouTube, tmp_path: Path) -> list[float]:
    heard: list[float] = []
    source.download_section(
        "https://youtu.be/Ab3_x-9QzLk", 970.0, 1130.0, tmp_path / "s.mp4", on_progress=heard.append
    )
    return heard


def test_section_downloaded_by_a_single_ffmpeg_runs_through_the_whole_download(
    tmp_path: Path,
) -> None:
    source = fake_yt_dlp(
        tmp_path,
        "out_time_us=40000000",
        "out_time_us=80000000",
        "out_time_us=120000000",
        "out_time_us=160000000",
        "wordcut-progress 5000 5000 NA",
    )

    assert section_progress(source, tmp_path) == [0.25, 0.5, 0.75, 1.0, 1.0]


def test_section_whose_video_and_audio_report_their_bytes_runs_through_both_without_going_back(
    tmp_path: Path,
) -> None:
    source = fake_yt_dlp(
        tmp_path,
        "wordcut-progress 450 900 NA",
        "wordcut-progress 900 900 NA",
        "wordcut-progress 50 100 NA",
        "wordcut-progress 100 100 NA",
    )

    assert section_progress(source, tmp_path) == [
        pytest.approx(0.45),
        0.9,
        pytest.approx(0.95),
        1.0,
    ]


def test_failed_download_is_a_youtube_error_that_hides_the_command_and_cookies(
    tmp_path: Path,
) -> None:
    source = fake_yt_dlp(tmp_path, "out_time_us=45000000", exit_code=1)

    with pytest.raises(YouTubeError) as raised:
        window_progress(source, tmp_path)

    message = str(raised.value)
    assert ("--cookies" in message, str(tmp_path) in message, "recusou" in message) == (
        False,
        False,
        True,
    )
