"""Caption text: punctuation and casing at the joins of a cut.

Joins need tidying: a segment cut after a comma ends the sentence on
screen; a hesitation ellipsis inside a sentence is dropped ("O modelo... Para
o marido" → "O modelo para o marido"); a function word capitalized mid-sentence
by the recognizer is lowered ("do que A sua" → "do que a sua").
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace

from wordcut.edit.cleanup import SENTENCE_END, TRAILING_MARKS, normalize
from wordcut.transcript import Word

_AFFIXES = re.compile(r"^(\W*)(.*?)(\W*)$", re.DOTALL)
CLAUSE_MARKS = (",", ";", ":")
FUNCTION_WORDS = frozenset(
    {"a", "o", "as", "os", "à", "ao", "e", "de", "do", "da", "em", "no", "na", "um", "uma",
     "que", "se", "por", "pra", "para", "com", "mas", "nem", "ou"}
)  # fmt: skip


def tidy_joins(words: Sequence[Word], segment_starts: Sequence[bool]) -> list[Word]:
    """Punctuation and casing fixes; ``segment_starts[i]`` marks a word opening a segment."""
    result = list(words)
    for index, word in enumerate(result):
        following_starts_segment = index + 1 < len(result) and segment_starts[index + 1]
        if following_starts_segment and word.text.endswith((*CLAUSE_MARKS, *TRAILING_MARKS)):
            result[index] = replace(word, text=word.text.rstrip(",;:.…").rstrip() + ".")
        elif index + 1 < len(result) and word.text.endswith(TRAILING_MARKS):
            result[index] = replace(word, text=word.text.rstrip(".…").rstrip())
    for index in range(1, len(result)):
        word, previous = result[index], result[index - 1]
        mid_sentence = not segment_starts[index] and not previous.text.endswith(SENTENCE_END)
        if mid_sentence and normalize(word.text) in FUNCTION_WORDS and word.text[:1].isupper():
            result[index] = replace(word, text=word.text[:1].lower() + word.text[1:])
    return result


def capitalize(word: Word) -> Word:
    prefix, core, suffix = _split(word.text)
    return replace(word, text=prefix + core[:1].upper() + core[1:] + suffix)


def _split(text: str) -> tuple[str, str, str]:
    match = _AFFIXES.match(text)
    assert match is not None  # the pattern matches any string
    prefix, core, suffix = match.groups()
    return prefix, core, suffix
