"""Human-readable transcript: one timestamped line per sentence."""

from __future__ import annotations

from collections.abc import Iterator

from wordcut.processing.sentences import split_sentences
from wordcut.timefmt import format_timestamp
from wordcut.transcript import Transcript


def overview_lines(
    transcript: Transcript, start: float = 0.0, end: float = float("inf")
) -> Iterator[str]:
    """``[HH:MM:SS.mmm] text`` lines, one per sentence (``split_sentences``)."""
    kept = [word for word in transcript.words if start <= word.start <= end]
    for sentence in split_sentences(kept):
        yield f"[{format_timestamp(sentence.start)}] {sentence.text}"


def word_lines(
    transcript: Transcript, start: float = 0.0, end: float = float("inf")
) -> Iterator[str]:
    """``start  end  word`` per word, for picking exact cut points."""
    for word in transcript.words:
        if start <= word.start <= end:
            yield f"{format_timestamp(word.start)}  {format_timestamp(word.end)}  {word.text}"
