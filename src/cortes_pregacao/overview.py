"""Human-readable transcript: one timestamped line per sentence."""

from __future__ import annotations

from collections.abc import Iterator

from cortes_pregacao.timefmt import format_timestamp
from cortes_pregacao.transcript import Transcript, Word

SENTENCE_END = (".", "?", "!")
MAX_WORDS_PER_LINE = 25
PAUSE_BREAK_S = 1.5


def overview_lines(
    transcript: Transcript, start: float = 0.0, end: float = float("inf")
) -> Iterator[str]:
    """``[HH:MM:SS.mmm] text`` lines, breaking on sentence ends, long pauses or length."""
    line: list[Word] = []
    for word in transcript.words:
        if not start <= word.start <= end:
            continue
        if line and word.start - line[-1].end > PAUSE_BREAK_S:
            yield _render(line)
            line = []
        line.append(word)
        if word.text.endswith(SENTENCE_END) or len(line) >= MAX_WORDS_PER_LINE:
            yield _render(line)
            line = []
    if line:
        yield _render(line)


def _render(words: list[Word]) -> str:
    return f"[{format_timestamp(words[0].start)}] " + " ".join(word.text for word in words)
