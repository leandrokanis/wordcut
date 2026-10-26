"""The spelling lock: a caption word may only be fixed to a word close to the original one,
so the fix never changes what was said (constitution §I; requirement 1.1.f.3).

The rule is the prototype's ``checkWord`` (docs/prototype/wordcut.html): the edit distance
between the cores of both words must not exceed a third of the original core.
"""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass

# The prototype's limit: about a third of the original word, never less than one edit.
LIMIT_SHARE = 0.34
MINIMUM_LIMIT = 1


@dataclass(frozen=True)
class SpellingCheck:
    """How far the proposed word is from the original and how far it may be."""

    distance: int
    limit: int

    @property
    def accepted(self) -> bool:
        return self.distance <= self.limit


def word_core(text: str) -> str:
    """The word in lower case with only its letters, digits and hyphens (Unicode), the part
    the lock compares: case, accents left apart and punctuation count for little."""
    composed = unicodedata.normalize("NFC", text).lower()
    return "".join(char for char in composed if _counts(char))


def _counts(char: str) -> bool:
    return char == "-" or unicodedata.category(char)[0] in ("L", "N")


def levenshtein(a: str, b: str) -> int:
    """The fewest insertions, deletions and substitutions that turn ``a`` into ``b``."""
    previous = list(range(len(b) + 1))
    for row, char_a in enumerate(a, start=1):
        current = [row]
        for column, char_b in enumerate(b, start=1):
            current.append(
                min(
                    previous[column] + 1,
                    current[column - 1] + 1,
                    previous[column - 1] + (char_a != char_b),
                )
            )
        previous = current
    return previous[-1]


def spelling_limit(original: str) -> int:
    """The largest distance a fix of ``original`` may have."""
    return max(MINIMUM_LIMIT, math.floor(LIMIT_SHARE * len(word_core(original))))


def check_spelling(original: str, proposed: str) -> SpellingCheck:
    """Compare the cores of ``original`` and ``proposed`` against the limit of ``original``."""
    return SpellingCheck(
        levenshtein(word_core(original), word_core(proposed)), spelling_limit(original)
    )
