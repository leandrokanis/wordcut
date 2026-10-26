"""The words a cut plays, segment by segment, with its assembled text and duration.

The duration is raw: the sum of each segment's span, pauses included; the cleanup the
export applies is not estimated here (spec 1.1.e.1, FR-004).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from wordcut.db.cuts import Segment
from wordcut.db.transcripts import WordRow

# Times are kept to the millisecond, the precision of HH:MM:SS.mmm (docs/cli.md §2).
MILLISECOND_DIGITS = 3


@dataclass(frozen=True)
class AssembledSegment:
    """The words of one segment, ``from_word`` to ``to_word`` inclusive, in sermon order."""

    from_word: int
    to_word: int
    words: tuple[WordRow, ...]

    @property
    def start(self) -> float:
        return self.words[0].start

    @property
    def end(self) -> float:
        return self.words[-1].end

    @property
    def text(self) -> str:
        return " ".join(word.text for word in self.words)


@dataclass(frozen=True)
class AssembledCut:
    """The segments of a cut in the order the cut plays them."""

    segments: tuple[AssembledSegment, ...]

    @property
    def text(self) -> str:
        return " ".join(segment.text for segment in self.segments)

    @property
    def duration(self) -> float:
        spans = sum(segment.end - segment.start for segment in self.segments)
        return round(spans, MILLISECOND_DIGITS)


def assemble(segments: Sequence[Segment], words: Sequence[WordRow]) -> AssembledCut:
    """The cut made of ``segments``, out of the sermon's ``words`` in spoken order."""
    # Word IDs are stable but not contiguous; the spoken order is the position (spec 1.1.e.1).
    place = {word.id: index for index, word in enumerate(words)}
    return AssembledCut(
        tuple(
            AssembledSegment(
                segment.from_word,
                segment.to_word,
                tuple(words[place[segment.from_word] : place[segment.to_word] + 1]),
            )
            for segment in segments
        )
    )
