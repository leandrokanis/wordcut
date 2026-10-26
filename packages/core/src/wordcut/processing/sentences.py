"""Sentences of a transcript: words grouped by sentence end, long pause or length."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from wordcut.transcript import Word

SENTENCE_END = (".", "?", "!")
MAX_WORDS_PER_SENTENCE = 25
PAUSE_BREAK_S = 1.5


@dataclass(frozen=True)
class Sentence:
    """Words ``first_word`` to ``last_word`` (indexes into the words, inclusive)."""

    first_word: int
    last_word: int
    start: float
    end: float
    text: str


def split_sentences(words: Sequence[Word]) -> list[Sentence]:
    """Group ``words`` into sentences.

    A sentence ends at a word ending in ``.``, ``?`` or ``!``, at its 25th word, or before
    a word that starts more than 1.5 s after the previous one ends.
    """
    sentences: list[Sentence] = []
    first = 0
    for index, word in enumerate(words):
        if index > first and word.start - words[index - 1].end > PAUSE_BREAK_S:
            sentences.append(_sentence(words, first, index - 1))
            first = index
        if word.text.endswith(SENTENCE_END) or index - first + 1 >= MAX_WORDS_PER_SENTENCE:
            sentences.append(_sentence(words, first, index))
            first = index + 1
    if first < len(words):
        sentences.append(_sentence(words, first, len(words) - 1))
    return sentences


def _sentence(words: Sequence[Word], first: int, last: int) -> Sentence:
    grouped = words[first : last + 1]
    return Sentence(
        first_word=first,
        last_word=last,
        start=grouped[0].start,
        end=grouped[-1].end,
        text=" ".join(word.text for word in grouped),
    )
