"""The continuous range of a cut, in sentences: snap it to sentence borders, cut its segments
down to it and shift the chosen sentences along with it (docs/cli.md §8.9).

Ranges and segments here are pairs of word positions (indexes into the sermon's words),
inclusive; times are in sermon time.
"""

from __future__ import annotations

from collections.abc import Sequence

from wordcut.processing.sentences import Sentence

Span = tuple[int, int]


def snap_range(sentences: Sequence[Sentence], start: float, end: float) -> Span:
    """The range from the first word of the sentence whose start is nearest ``start`` to the
    last word of the sentence whose end is nearest ``end``; a tie goes to the earlier one.
    It may come out backwards, which the caller refuses."""
    first = min(sentences, key=lambda sentence: abs(sentence.start - start))
    last = min(sentences, key=lambda sentence: abs(sentence.end - end))
    return first.first_word, last.last_word


def trim_segments(segments: Sequence[Span], within: Span) -> list[Span]:
    """``segments`` cut down to the words ``within`` the range, in the order given; a segment
    with no word inside is dropped."""
    first, last = within
    trimmed = [(max(start, first), min(end, last)) for start, end in segments]
    return [(start, end) for start, end in trimmed if start <= end]


def shift_selection(
    sentences: Sequence[Sentence],
    segments: Sequence[Span],
    current: tuple[float, float],
    by: float,
) -> tuple[Span, list[Span]]:
    """The range ``current`` (start and end times) shifted ``by`` seconds, no further than the
    sermon's first and last sentences, and snapped, and the segments that take each chosen
    sentence to the sentence of the new range whose start is nearest its own shifted start.

    The chosen sentences go in the order the segments first touch them, each whole even when
    only part of it was chosen, and each destination takes one sentence only; neighbouring
    destinations played one after the other join into one segment.
    """
    start, end = current
    shift = min(max(by, sentences[0].start - start), sentences[-1].end - end)
    shifted = snap_range(sentences, start + shift, end + shift)
    first, last = shifted
    free = [sentence for sentence in sentences if first <= sentence.first_word <= last]
    moved: list[Span] = []
    for sentence in _chosen(sentences, segments):
        if not free:
            break
        target = min(free, key=lambda candidate: abs(candidate.start - sentence.start - shift))
        free.remove(target)
        if moved and moved[-1][1] + 1 == target.first_word:
            moved[-1] = (moved[-1][0], target.last_word)
        else:
            moved.append((target.first_word, target.last_word))
    return shifted, moved


def _chosen(sentences: Sequence[Sentence], segments: Sequence[Span]) -> list[Sentence]:
    """The sentences with a word in ``segments``, in the order the segments first touch them."""
    chosen: list[Sentence] = []
    for start, end in segments:
        for sentence in sentences:
            touched = sentence.first_word <= end and start <= sentence.last_word
            if touched and sentence not in chosen:
                chosen.append(sentence)
    return chosen
