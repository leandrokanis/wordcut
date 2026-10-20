"""Word-level transcript model and its JSON representation."""

from __future__ import annotations

import json
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Word:
    """A spoken word with start/end times in seconds.

    ``estimated`` is true when the aligner could not place the word and its
    times were interpolated from its neighbours.
    """

    text: str
    start: float
    end: float
    score: float | None = None
    estimated: bool = False

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError(f"word {self.text!r} ends before it starts ({self.start}>{self.end})")

    @property
    def duration(self) -> float:
        return self.end - self.start

    def shifted(self, delta: float) -> Word:
        return replace(self, start=self.start + delta, end=self.end + delta)


@dataclass(frozen=True)
class Transcript:
    """Ordered words of a media file, with times relative to that file."""

    words: tuple[Word, ...]
    language: str
    model: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def text(self) -> str:
        return " ".join(word.text for word in self.words)

    def shifted(self, delta: float) -> Transcript:
        return replace(self, words=tuple(word.shifted(delta) for word in self.words))

    def between(self, start: float, end: float) -> Transcript:
        """Words fully inside ``[start, end]``, rebased so ``start`` becomes 0."""
        kept = tuple(
            word.shifted(-start) for word in self.words if word.start >= start and word.end <= end
        )
        return replace(self, words=kept)

    def to_json(self) -> dict[str, Any]:
        return {
            "version": SCHEMA_VERSION,
            "language": self.language,
            "model": self.model,
            "metadata": self.metadata,
            "words": [asdict(word) for word in self.words],
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Transcript:
        version = data.get("version")
        if version != SCHEMA_VERSION:
            raise ValueError(f"unsupported transcript version: {version!r}")
        return cls(
            words=tuple(Word(**word) for word in data["words"]),
            language=data["language"],
            model=data["model"],
            metadata=data.get("metadata", {}),
        )

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=1), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Transcript:
        return cls.from_json(json.loads(path.read_text(encoding="utf-8")))


@dataclass(frozen=True)
class RawWord:
    """A word as produced by the aligner, possibly without times."""

    text: str
    start: float | None = None
    end: float | None = None
    score: float | None = None


def fill_missing_times(raw_words: Sequence[RawWord], total_duration: float) -> list[Word]:
    """Turn aligner output into timed words.

    Runs of words without times share the gap between the previous timed word's
    end and the next timed word's start evenly. Such words are marked
    ``estimated``.
    """
    words: list[Word] = []
    index = 0
    while index < len(raw_words):
        raw = raw_words[index]
        if raw.start is not None and raw.end is not None:
            words.append(Word(raw.text, raw.start, raw.end, raw.score))
            index += 1
            continue

        run_end = index
        while run_end < len(raw_words) and _is_untimed(raw_words[run_end]):
            run_end += 1
        gap_start = words[-1].end if words else 0.0
        gap_end = _next_start(raw_words, run_end, default=total_duration)
        words.extend(_spread(raw_words[index:run_end], gap_start, max(gap_start, gap_end)))
        index = run_end
    return words


def _is_untimed(raw: RawWord) -> bool:
    return raw.start is None or raw.end is None


def _next_start(raw_words: Sequence[RawWord], index: int, default: float) -> float:
    if index < len(raw_words):
        start = raw_words[index].start
        if start is not None:
            return start
    return default


def _spread(run: Iterable[RawWord], start: float, end: float) -> list[Word]:
    run = list(run)
    step = (end - start) / len(run)
    return [
        Word(raw.text, start + i * step, start + (i + 1) * step, raw.score, estimated=True)
        for i, raw in enumerate(run)
    ]
