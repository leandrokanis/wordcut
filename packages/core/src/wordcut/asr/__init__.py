"""Speech recognition with word-level timestamps."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol


class Transcriber(Protocol):
    def transcribe(
        self, audio: Path, output: Path, *, on_progress: Callable[[float], None] | None = None
    ) -> None:
        """Write a :class:`~wordcut.transcript.Transcript` JSON for ``audio``; ``on_progress``
        hears how far the transcription is, from 0 to 1."""
