"""Per-sermon folder layout.

::

    <root>/AAAA-MM-DD - Título - Referência/
        AAAA-MM-DD - Título - Referência.mp4   sermon, horizontal
        palavras.json                          words, times relative to the mp4
        roteiros/                              approved edit lists (one per short)
        cortes/                                vertical shorts
        trabalho/                              intermediates; safe to delete
"""

from __future__ import annotations

import platform
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

LIVE_AUDIO = "live-audio.m4a"
LIVE_WORDS = "live-palavras.json"
SECTION_VIDEO = "fonte_trecho.mp4"


def default_root() -> Path:
    videos = "Movies" if platform.system() == "Darwin" else "Videos"
    return Path.home() / videos / "Pregações"


def folder_name(service_date: date, title: str, reference: str | None = None) -> str:
    """``2026-10-18 - Título - Ester 4.13-16``; ``:`` in references becomes ``.``."""
    parts = [service_date.isoformat(), _clean(title)]
    if reference:
        parts.append(_clean(reference.replace(":", ".")))
    return " - ".join(parts)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r'[/\\:*?"<>|]', "", text)).strip()


@dataclass(frozen=True)
class SermonFolder:
    path: Path

    @property
    def sermon_video(self) -> Path:
        return self.path / f"{self.path.name}.mp4"

    @property
    def words(self) -> Path:
        return self.path / "palavras.json"

    @property
    def work(self) -> Path:
        return self.path / "trabalho"

    @property
    def live_audio(self) -> Path:
        return self.work / LIVE_AUDIO

    @property
    def live_words(self) -> Path:
        return self.work / LIVE_WORDS

    @property
    def section_video(self) -> Path:
        return self.work / SECTION_VIDEO

    def create(self) -> SermonFolder:
        for sub in ("roteiros", "cortes", "trabalho"):
            (self.path / sub).mkdir(parents=True, exist_ok=True)
        return self
