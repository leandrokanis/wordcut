"""YouTube access through yt-dlp."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

CHURCH_TIMEZONE = ZoneInfo("America/Sao_Paulo")
DEFAULT_COOKIES = Path.home() / ".config/cortes-pregacao/youtube-cookies.txt"
# yt-dlp's static ffmpeg build; Ubuntu's ffmpeg 6.1 segfaults on section downloads.
DEFAULT_FFMPEG_DIR = Path.home() / ".local/share/cortes-pregacao/ffmpeg/bin"
MAX_HEIGHT = 1080


@dataclass(frozen=True)
class LiveInfo:
    title: str
    service_date: date
    duration: float
    live_status: str

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> LiveInfo:
        """Build from yt-dlp's JSON.

        ``upload_date`` is in UTC, so an evening service shows up as the next
        day; the stream's start time in the church's timezone gives the right date.
        """
        timestamp = metadata.get("release_timestamp") or metadata.get("timestamp")
        if timestamp is None:
            raise ValueError("vídeo sem horário de início; informe a data manualmente")
        return cls(
            title=metadata["title"],
            service_date=datetime.fromtimestamp(timestamp, CHURCH_TIMEZONE).date(),
            duration=float(metadata["duration"]),
            live_status=metadata.get("live_status") or "not_live",
        )

    @property
    def is_finished(self) -> bool:
        return self.live_status in {"was_live", "not_live"}


class YouTube:
    def __init__(
        self, cookies: Path = DEFAULT_COOKIES, ffmpeg_dir: Path | None = DEFAULT_FFMPEG_DIR
    ) -> None:
        self._cookies = cookies
        self._ffmpeg_dir = ffmpeg_dir if ffmpeg_dir and ffmpeg_dir.is_dir() else None

    def info(self, url: str) -> LiveInfo:
        output = self._run(["--dump-single-json", "--skip-download", url], capture=True)
        return LiveInfo.from_metadata(json.loads(output))

    def download_audio(self, url: str, output: Path) -> Path:
        """Whole audio track as m4a; ``output`` must end in ``.m4a``."""
        self._run(["-f", "ba[ext=m4a]/ba", "-o", str(output), url])
        return output

    def download_section(self, url: str, start: float, end: float, output: Path) -> Path:
        """Video+audio between ``start`` and ``end`` (seconds), up to 1080p, as mp4.

        The section starts at a keyframe near ``start``, not exactly at it; use
        :func:`cortes_pregacao.sync.locate_clip` to find the real offset.
        """
        self._run(self.section_args(url, start, end, output))
        return output

    @staticmethod
    def section_args(url: str, start: float, end: float, output: Path) -> list[str]:
        return [
            "-f", f"bv*[height<={MAX_HEIGHT}]+ba/b[height<={MAX_HEIGHT}]",
            "--download-sections", f"*{start:.3f}-{end:.3f}",
            "--merge-output-format", "mp4",
            "-o", str(output),
            url,
        ]  # fmt: skip

    def base_command(self) -> list[str]:
        command = ["yt-dlp", "--quiet", "--no-warnings", "--cookies", str(self._cookies)]
        if self._ffmpeg_dir:
            command += ["--ffmpeg-location", str(self._ffmpeg_dir)]
        return command

    def _run(self, args: list[str], capture: bool = False) -> str:
        if not self._cookies.exists():
            raise FileNotFoundError(
                f"arquivo de cookies não encontrado: {self._cookies} (veja o README)"
            )
        command = self.base_command() + args
        result = subprocess.run(command, check=True, capture_output=capture, text=True)
        return result.stdout if capture else ""
