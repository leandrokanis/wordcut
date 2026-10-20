"""Caption text: spelling corrections and sentence-case at segment starts.

Speech recognition spells proper names inconsistently ("Esther", "Esté"), so
an edit list carries phrase corrections, applied word by word so each word
keeps its own timing and punctuation.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import replace

from cortes_pregacao.edit.cleanup import normalize
from cortes_pregacao.transcript import Word

_AFFIXES = re.compile(r"^(\W*)(.*?)(\W*)$", re.DOTALL)


def validate_corrections(corrections: Mapping[str, str]) -> None:
    for wrong, right in corrections.items():
        if len(wrong.split()) != len(right.split()):
            raise ValueError(
                f"correção precisa ter o mesmo número de palavras: {wrong!r} -> {right!r}"
            )


def apply_corrections(words: Sequence[Word], corrections: Mapping[str, str]) -> list[Word]:
    result = list(words)
    tokens = [normalize(word.text) for word in words]
    for wrong, right in corrections.items():
        pattern = [normalize(token) for token in wrong.split()]
        replacement = right.split()
        for start in range(len(result) - len(pattern) + 1):
            if tokens[start : start + len(pattern)] == pattern:
                for offset, new in enumerate(replacement):
                    index = start + offset
                    result[index] = replace(result[index], text=_retext(result[index].text, new))
    return result


def capitalize(word: Word) -> Word:
    prefix, core, suffix = _split(word.text)
    return replace(word, text=prefix + core[:1].upper() + core[1:] + suffix)


def _retext(original: str, new_core: str) -> str:
    prefix, core, suffix = _split(original)
    if core[:1].isupper():
        new_core = new_core[:1].upper() + new_core[1:]
    return prefix + new_core + suffix


def _split(text: str) -> tuple[str, str, str]:
    match = _AFFIXES.match(text)
    assert match is not None  # the pattern matches any string
    prefix, core, suffix = match.groups()
    return prefix, core, suffix
