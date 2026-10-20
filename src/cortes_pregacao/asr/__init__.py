"""Speech recognition with word-level timestamps."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Transcriber(Protocol):
    def transcribe(self, audio: Path, output: Path) -> None:
        """Write a :class:`~cortes_pregacao.transcript.Transcript` JSON for ``audio``."""
