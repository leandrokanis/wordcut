"""Hesitation detection.

Conservative on purpose: a word is only dropped when it cannot carry meaning.

- Fillers: "hã", "hum", "né"… always. "é" is also a verb, so it (like "então",
  "aí") only counts when the recognizer marked it as trailing off ("é...").
- Word stammer: a short function word said twice ("o, o Senhor"). Longer words
  are left alone, so rhetorical repetition ("santo, santo, santo") survives.
- Phrase stammer: a 2-3 word phrase restarted right away, the first attempt
  trailing off with a comma or ellipsis ("não teve, não teve sonho").

When a dropped word carried the sentence end ("insônia, né."), the full stop
moves to the previous word, so captions and pause timing still see it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, replace

from wordcut.transcript import Word

FILLERS = frozenset({"hã", "ãh", "ah", "ahn", "eh", "éh", "hum", "hmm", "hm", "uh", "uhm", "né"})
TRAILING_FILLERS = frozenset({"é", "e", "então", "aí"})
STAMMER_MAX_LETTERS = 3
STAMMER_MAX_GAP_S = 0.8
PHRASE_STAMMER_LENGTHS = (3, 2)
TRAILING_MARKS = ("...", "…")
RESTART_MARKS = (",", *TRAILING_MARKS)
SENTENCE_END = (".", "?", "!")


@dataclass(frozen=True)
class CleanupResult:
    kept: tuple[Word, ...]
    removed: tuple[Word, ...]


def remove_hesitations(words: Sequence[Word]) -> CleanupResult:
    dropped = _hesitation_indexes(words)
    kept: list[Word] = []
    removed: list[Word] = []
    for index, word in enumerate(words):
        if index not in dropped:
            kept.append(word)
            continue
        removed.append(word)
        if kept and word.text.endswith(SENTENCE_END) and index - 1 not in dropped:
            kept[-1] = _end_sentence(kept[-1], word.text[-1])
    return CleanupResult(tuple(kept), tuple(removed))


def normalize(text: str) -> str:
    return re.sub(r"[^\w]", "", text.lower())


def _hesitation_indexes(words: Sequence[Word]) -> set[int]:
    dropped = {i for i, word in enumerate(words) if _is_filler(word)}
    dropped |= {i for i in range(len(words) - 1) if _is_word_stammer(words[i], words[i + 1])}
    dropped |= _phrase_stammers(words)
    return dropped


def _is_filler(word: Word) -> bool:
    token = normalize(word.text)
    if token in FILLERS:
        return True
    return token in TRAILING_FILLERS and word.text.rstrip().endswith(TRAILING_MARKS)


def _is_word_stammer(word: Word, following: Word) -> bool:
    token = normalize(word.text)
    return (
        0 < len(token) <= STAMMER_MAX_LETTERS
        and token == normalize(following.text)
        and following.start - word.end <= STAMMER_MAX_GAP_S
    )


def _phrase_stammers(words: Sequence[Word]) -> set[int]:
    tokens = [normalize(word.text) for word in words]
    dropped: set[int] = set()
    for start in range(len(words)):
        for length in PHRASE_STAMMER_LENGTHS:
            first = range(start, start + length)
            again = start + length
            if again + length > len(words) or dropped & set(first):
                continue
            if (
                tokens[start:again] == tokens[again : again + length]
                and words[again - 1].text.endswith(RESTART_MARKS)
                and words[again].start - words[again - 1].end <= STAMMER_MAX_GAP_S
            ):
                dropped |= set(first)
                break
    return dropped


def _end_sentence(word: Word, mark: str) -> Word:
    if word.text.endswith(SENTENCE_END):
        return word
    return replace(word, text=word.text.rstrip(",;:") + mark)
