"""YouTube access through yt-dlp."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import ParseResult, parse_qs, urlparse
from zoneinfo import ZoneInfo

import httpx

from wordcut import config
from wordcut.errors import WordcutError

CHURCH_TIMEZONE = ZoneInfo("America/Sao_Paulo")
# yt-dlp's static ffmpeg build; Ubuntu's ffmpeg 6.1 segfaults on section downloads.
DEFAULT_FFMPEG_DIR = Path.home() / ".local/share/wordcut/ffmpeg/bin"
MAX_HEIGHT = 1080
AUDIO_FORMAT = "ba[ext=m4a]/ba"
# The waveform needs only how loud the audio is, so the smallest audio of the live will do.
LOWEST_AUDIO_FORMAT = "worstaudio"
FETCH_TIMEOUT_SECONDS = 30.0

VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
YOUTUBE_HOSTS = frozenset({"youtube.com", "www.youtube.com", "m.youtube.com"})
SHORT_LINK_HOST = "youtu.be"
PATH_PREFIXES = ("/live/", "/shorts/")

# yt-dlp downloads a section through ffmpeg and reports its own progress only once it ends
# (yt_dlp/downloader/external.py, FFmpegFD), so ffmpeg reports the media time it has written.
# --progress prints even under --quiet.
BYTES_PREFIX = "wordcut-progress"
DOWNLOAD_PROGRESS_ARGS = (
    "--newline",
    "--progress",
    "--progress-template",
    f"download:{BYTES_PREFIX} %(progress.downloaded_bytes)s %(progress.total_bytes)s"
    " %(progress.total_bytes_estimate)s",
    "--downloader-args",
    "ffmpeg_o:-progress pipe:1",
)
MEDIA_TIME = re.compile(r"out_time_us=(\d+)")
DOWNLOADED_BYTES = re.compile(rf"{BYTES_PREFIX} (\d+) (\S+) (\S+)")
MICROSECONDS = 1_000_000
# Share of the section download each of its parts takes when yt-dlp downloads the video and
# the audio one after the other and reports their bytes; the audio is much smaller. A section
# downloaded by a single ffmpeg (which already joins video and audio) reports its media time
# for the whole section instead.
SECTION_PARTS = (0.9, 0.1)
WHOLE = (1.0,)


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
        self,
        cookies: Path | None = None,
        ffmpeg_dir: Path | None = DEFAULT_FFMPEG_DIR,
        program: Sequence[str] = ("yt-dlp",),
    ) -> None:
        """``cookies`` defaults to the file in the secrets folder, resolved now; ``program``
        is how yt-dlp is started."""
        self._cookies = cookies or config.youtube_cookies()
        self._ffmpeg_dir = ffmpeg_dir if ffmpeg_dir and ffmpeg_dir.is_dir() else None
        self._program = tuple(program)

    def info(self, url: str) -> LiveInfo:
        try:
            return LiveInfo.from_metadata(self.metadata(url))
        except ValueError:
            raise YouTubeError(
                "O vídeo não tem horário de início no YouTube; sem ele não há data do culto."
            ) from None

    def metadata(self, url: str) -> dict[str, Any]:
        """What yt-dlp knows about the video, its formats included, without downloading it."""
        output = self._run(["--dump-single-json", "--skip-download", url], capture=True)
        try:
            metadata: dict[str, Any] = json.loads(output)
        except json.JSONDecodeError:
            raise YouTubeError("O YouTube devolveu dados ilegíveis sobre o vídeo.") from None
        return metadata

    def download_audio(self, url: str, output: Path) -> Path:
        """Only the audio of the whole video, in its lowest quality, in its own format."""
        self._run(["-f", LOWEST_AUDIO_FORMAT, "-o", str(output), url])
        return output

    @staticmethod
    def fetch(url: str, output: Path) -> Path:
        """The file at ``url``, such as an image of a storyboard, saved as ``output``."""
        try:
            response = httpx.get(url, timeout=FETCH_TIMEOUT_SECONDS, follow_redirects=True)
            response.raise_for_status()
        except httpx.HTTPError:
            raise YouTubeError(REFUSED) from None
        output.write_bytes(response.content)
        return output

    def download_audio_window(
        self,
        url: str,
        start: float,
        end: float,
        output: Path,
        *,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        """Audio only between ``start`` and ``end`` (seconds), as m4a.

        Unlike :meth:`download_section`, an audio section starts exactly at ``start``.
        """
        self._download(
            self.audio_window_args(url, start, end, output), end - start, WHOLE, on_progress
        )
        return output

    @staticmethod
    def audio_window_args(url: str, start: float, end: float, output: Path) -> list[str]:
        return [
            "-f", AUDIO_FORMAT,
            "--download-sections", f"*{start:.3f}-{end:.3f}",
            "-o", str(output),
            url,
        ]  # fmt: skip

    def download_section(
        self,
        url: str,
        start: float,
        end: float,
        output: Path,
        *,
        on_progress: Callable[[float], None] | None = None,
    ) -> Path:
        """Video+audio between ``start`` and ``end`` (seconds), up to 1080p, as mp4.

        The section starts at a keyframe near ``start``, not exactly at it; use
        :func:`wordcut.sync.locate_clip` to find the real offset.
        """
        self._download(
            self.section_args(url, start, end, output), end - start, SECTION_PARTS, on_progress
        )
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
        command = [*self._program, "--quiet", "--no-warnings", "--cookies", str(self._cookies)]
        if self._ffmpeg_dir:
            command += ["--ffmpeg-location", str(self._ffmpeg_dir)]
        return command

    def _run(self, args: list[str], capture: bool = False) -> str:
        command = self._command(args)
        try:
            result = subprocess.run(command, check=True, capture_output=capture, text=True)
        except subprocess.CalledProcessError:
            raise YouTubeError(REFUSED) from None
        return result.stdout if capture else ""

    def _download(
        self,
        args: list[str],
        seconds: float,
        shares: tuple[float, ...],
        on_progress: Callable[[float], None] | None,
    ) -> None:
        """Run a section download of ``seconds`` made of parts taking ``shares`` of it,
        telling ``on_progress`` how far the whole download is."""
        command = self._command([*DOWNLOAD_PROGRESS_ARGS, *args])
        parts = _Parts(shares)
        with subprocess.Popen(command, stdout=subprocess.PIPE, text=True) as process:
            assert process.stdout is not None
            for line in process.stdout:
                reading = _reading(line.strip(), seconds)
                if reading is not None and on_progress is not None:
                    on_progress(parts.overall(*reading))
        if process.returncode != 0:
            raise YouTubeError(REFUSED)

    def _command(self, args: list[str]) -> list[str]:
        if not self._cookies.exists():
            raise YouTubeError(
                "Arquivo de cookies do YouTube não encontrado na pasta de segredos (veja o README)."
            )
        return self.base_command() + args


REFUSED = (
    "O YouTube recusou o pedido: o vídeo pode não existir, ser privado ou a rede pode ter falhado."
)


class _Parts:
    """The parts of a download, one after the other: a part starts when the progress of the
    current one goes back. Once ffmpeg reports media time, a single process is downloading
    the whole thing, so its parts no longer apply."""

    def __init__(self, shares: tuple[float, ...]) -> None:
        self._shares = shares
        self._part = 0
        self._last = 0.0
        self._single_process = False

    def overall(self, fraction: float, media_time: bool) -> float:
        """How far the whole download is when the current part is at ``fraction``, told by
        ffmpeg's ``media_time`` or by yt-dlp's bytes."""
        fraction = min(fraction, 1.0)
        self._single_process = self._single_process or media_time
        if self._single_process:
            return fraction
        if fraction < self._last and self._part + 1 < len(self._shares):
            self._part += 1
        self._last = fraction
        return sum(self._shares[: self._part]) + self._shares[self._part] * fraction


def _reading(line: str, seconds: float) -> tuple[float, bool] | None:
    """How far a download of ``seconds`` of media is, if ``line`` tells it, and whether it
    is the media time ffmpeg has written rather than the bytes yt-dlp has over their total
    or its estimate."""
    media_time = MEDIA_TIME.fullmatch(line)
    if media_time is not None:
        if seconds <= 0:
            return None
        return int(media_time.group(1)) / MICROSECONDS / seconds, True
    downloaded = DOWNLOADED_BYTES.fullmatch(line)
    if downloaded is None:
        return None
    total = _number(downloaded.group(2)) or _number(downloaded.group(3))
    return (int(downloaded.group(1)) / total, False) if total else None


def _number(text: str) -> float | None:
    """yt-dlp writes ``NA`` for a value it does not know."""
    try:
        return float(text)
    except ValueError:
        return None
