"""Hesitation detection.

Conservative on purpose: a word is only dropped when it cannot carry meaning.
"é" is a verb in Portuguese, so it only counts as a hesitation when the
recognizer marked it as trailing off ("é..."). Repeated words count as a
stammer only for short function words ("o, o Senhor"), so rhetorical
repetition ("santo, santo, santo") survives.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from cortes_pregacao.transcript import Word

FILLERS = frozenset({"hã", "ãh", "ah", "ahn", "eh", "éh", "hum", "hmm", "hm", "uh", "uhm", "né"})
TRAILING_FILLERS = frozenset({"é", "e", "então", "aí"})
STAMMER_MAX_LETTERS = 3
STAMMER_MAX_GAP_S = 0.8
TRAILING_MARKS = ("...", "…")


@dataclass(frozen=True)
class CleanupResult:
    kept: tuple[Word, ...]
    removed: tuple[Word, ...]


def remove_hesitations(words: Sequence[Word]) -> CleanupResult:
    kept: list[Word] = []
    removed: list[Word] = []
    for index, word in enumerate(words):
        following = words[index + 1] if index + 1 < len(words) else None
        if _is_filler(word) or _is_stammer(word, following):
            removed.append(word)
        else:
            kept.append(word)
    return CleanupResult(tuple(kept), tuple(removed))


def normalize(text: str) -> str:
    return re.sub(r"[^\w]", "", text.lower())


def _is_filler(word: Word) -> bool:
    token = normalize(word.text)
    if token in FILLERS:
        return True
    return token in TRAILING_FILLERS and word.text.rstrip().endswith(TRAILING_MARKS)


def _is_stammer(word: Word, following: Word | None) -> bool:
    if following is None:
        return False
    token = normalize(word.text)
    return (
        0 < len(token) <= STAMMER_MAX_LETTERS
        and token == normalize(following.text)
        and following.start - word.end <= STAMMER_MAX_GAP_S
    )
