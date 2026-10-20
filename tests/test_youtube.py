from datetime import date
from pathlib import Path

import pytest

from cortes_pregacao.youtube import LiveInfo, YouTube


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


def test_missing_cookies_file_is_explained(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="cookies"):
        YouTube(cookies=tmp_path / "none.txt").info("URL")


def test_uses_bundled_ffmpeg_when_installed(tmp_path: Path) -> None:
    command = YouTube(cookies=tmp_path / "c.txt", ffmpeg_dir=tmp_path).base_command()

    assert command[command.index("--ffmpeg-location") + 1] == str(tmp_path)


def test_falls_back_to_system_ffmpeg(tmp_path: Path) -> None:
    command = YouTube(cookies=tmp_path / "c.txt", ffmpeg_dir=tmp_path / "missing").base_command()

    assert "--ffmpeg-location" not in command
