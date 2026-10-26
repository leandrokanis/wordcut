"""YouTube access through yt-dlp."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import ParseResult, parse_qs, urlparse
from zoneinfo import ZoneInfo

from wordcut import config
from wordcut.errors import WordcutError

CHURCH_TIMEZONE = ZoneInfo("America/Sao_Paulo")
# yt-dlp's static ffmpeg build; Ubuntu's ffmpeg 6.1 segfaults on section downloads.
DEFAULT_FFMPEG_DIR = Path.home() / ".local/share/wordcut/ffmpeg/bin"
MAX_HEIGHT = 1080

VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com"})
SHORT_LINK_HOST = "youtu.be"
PATH_PREFIXES = ("/live/", "/shorts/")


def video_id(url: str) -> str:
    """The 11-character ID of the video ``url`` points to.

    Accepts ``watch?v=``, ``youtu.be/``, ``/live/`` and ``/shorts/`` links, over http or
    https; anything else is an ``invalid_argument`` error on the ``link`` argument.
    """
    candidate = _id_candidate(urlparse(url))
    if candidate is None or not VIDEO_ID.fullmatch(candidate):
        raise WordcutError(
            "invalid_argument",
            "Link inválido: informe o link de um vídeo do YouTube.",
            {"argument": "link"},
        )
    return candidate


def _id_candidate(link: ParseResult) -> str | None:
    if link.scheme not in {"http", "https"}:
        return None
    if link.netloc == SHORT_LINK_HOST:
        return link.path.removeprefix("/")
    if link.netloc not in YOUTUBE_HOSTS:
        return None
    if link.path == "/watch":
        return parse_qs(link.query).get("v", [""])[0]
    for prefix in PATH_PREFIXES:
        if link.path.startswith(prefix):
            return link.path.removeprefix(prefix)
    return None


class YouTubeError(Exception):
    """YouTube could not answer; the message is Portuguese and safe to show.

    It never carries the yt-dlp command nor the path of the cookies file.
    """


@dataclass(frozen=True)
class LiveInfo:
    title: str
    service_date: date
    duration: float | None
    live_status: str

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any]) -> LiveInfo:
        """Build from yt-dlp's JSON.

        ``upload_date`` is in UTC, so an evening service shows up as the next
        day; the stream's start time in the church's timezone gives the right date.
        """
        timestamp = metadata.get("release_timestamp") or metadata.get("timestamp")
        # yt-dlp may leave out the duration of a stream that is still live.
        duration = metadata.get("duration")
        if timestamp is None:
            raise ValueError("vídeo sem horário de início; informe a data manualmente")
        return cls(
            title=metadata["title"],
            service_date=datetime.fromtimestamp(timestamp, CHURCH_TIMEZONE).date(),
            duration=None if duration is None else float(duration),
            live_status=metadata.get("live_status") or "not_live",
        )

    @property
    def is_finished(self) -> bool:
        return self.live_status in {"was_live", "not_live"}


class LiveSource(Protocol):
    """Where the data of a live comes from; ``YouTube`` in production, a double in tests."""

    def info(self, url: str) -> LiveInfo: ...


class YouTube:
    def __init__(
        self, cookies: Path | None = None, ffmpeg_dir: Path | None = DEFAULT_FFMPEG_DIR
    ) -> None:
        """``cookies`` defaults to the file in the secrets folder, resolved now."""
        self._cookies = cookies or config.youtube_cookies()
        self._ffmpeg_dir = ffmpeg_dir if ffmpeg_dir and ffmpeg_dir.is_dir() else None

    def info(self, url: str) -> LiveInfo:
        output = self._run(["--dump-single-json", "--skip-download", url], capture=True)
        try:
            metadata = json.loads(output)
        except json.JSONDecodeError:
            raise YouTubeError("O YouTube devolveu dados ilegíveis sobre o vídeo.") from None
        try:
            return LiveInfo.from_metadata(metadata)
        except ValueError:
            raise YouTubeError(
                "O vídeo não tem horário de início no YouTube; sem ele não há data do culto."
            ) from None

    def download_audio(self, url: str, output: Path) -> Path:
        """Whole audio track as m4a; ``output`` must end in ``.m4a``."""
        self._run(["-f", "ba[ext=m4a]/ba", "-o", str(output), url])
        return output

    def download_section(self, url: str, start: float, end: float, output: Path) -> Path:
        """Video+audio between ``start`` and ``end`` (seconds), up to 1080p, as mp4.

        The section starts at a keyframe near ``start``, not exactly at it; use
        :func:`wordcut.sync.locate_clip` to find the real offset.
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
            raise YouTubeError(
                "Arquivo de cookies do YouTube não encontrado na pasta de segredos (veja o README)."
            )
        command = self.base_command() + args
        try:
            result = subprocess.run(command, check=True, capture_output=capture, text=True)
        except subprocess.CalledProcessError:
            raise YouTubeError(
                "O YouTube recusou o pedido: o vídeo pode não existir, ser privado"
                " ou a rede pode ter falhado."
            ) from None
        return result.stdout if capture else ""
