"""Edit list ("roteiro"): the ordered sermon excerpts that make up one short.

Times are relative to the sermon video. Segments may be out of chronological
order (e.g. a hook taken from the conclusion); each one carries a note that
justifies why the meaning is preserved.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    note: str = ""

    def __post_init__(self) -> None:
        if not 0 <= self.start < self.end:
            raise ValueError(f"trecho inválido: {self.start} -> {self.end}")


@dataclass(frozen=True)
class EditList:
    title: str
    segments: tuple[Segment, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise ValueError("roteiro sem trechos")

    def reordered(self) -> list[int]:
        """Indexes of segments taken from further ahead in the sermon.

        A segment is out of order when some later segment comes from earlier in
        the sermon — typically a hook lifted from the conclusion. These are the
        segments whose ``note`` must justify that the meaning is preserved.
        """
        starts = [segment.start for segment in self.segments]
        return [
            i for i, start in enumerate(starts) if any(later < start for later in starts[i + 1 :])
        ]

    def to_json(self) -> dict[str, Any]:
        return {
            "version": SCHEMA_VERSION,
            "title": self.title,
            "segments": [asdict(segment) for segment in self.segments],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> EditList:
        if data.get("version") != SCHEMA_VERSION:
            raise ValueError(f"versão de roteiro não suportada: {data.get('version')!r}")
        return cls(
            title=data["title"],
            segments=tuple(Segment(**segment) for segment in data["segments"]),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> EditList:
        return cls.from_json(json.loads(path.read_text(encoding="utf-8")))
