"""The words of a timeline as the captions show them."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from wordcut.edit.text import capitalize, tidy_joins
from wordcut.edit.timeline import Timeline
from wordcut.transcript import Word

Respell = Callable[[Sequence[Word]], list[Word]]
"""The same words, in the same order and times, with some of them spelled differently."""


def caption_words(timeline: Timeline, respell: Respell = list) -> list[Word]:
    """The kept words as shown on screen, on the short's own clock: spelled by ``respell``
    (which sees source times), tidied at joins, and capitalized where a segment begins."""
    respelled = iter(respell([word for clip in timeline.clips for word in clip.words]))
    words: list[Word] = []
    starts: list[bool] = []
    offset, previous_segment = 0.0, None
    for clip in timeline.clips:
        for index in range(len(clip.words)):
            words.append(next(respelled).shifted(offset - clip.start))
            starts.append(index == 0 and clip.segment != previous_segment)
        offset += clip.duration
        previous_segment = clip.segment
    words = tidy_joins(words, starts)
    return [capitalize(w) if start else w for w, start in zip(words, starts, strict=True)]
