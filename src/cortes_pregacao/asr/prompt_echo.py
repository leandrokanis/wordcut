"""Remove decoder-prompt echoes from recognized words.

Whisper sometimes "hallucinates" its initial prompt as speech, typically during
music. Those words would look like real hesitations to the editor, so runs that
reproduce a contiguous stretch of the prompt are dropped.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TypeVar

from cortes_pregacao.transcript import RawWord, Word

MIN_ECHO_RUN = 4

W = TypeVar("W", Word, RawWord)


def remove_prompt_echoes(words: Sequence[W], prompt: str, min_run: int = MIN_ECHO_RUN) -> list[W]:
    prompt_tokens = [_normalize(token) for token in prompt.split()]
    prompt_ngrams = {
        tuple(prompt_tokens[i : i + min_run]) for i in range(len(prompt_tokens) - min_run + 1)
    }
    tokens = [_normalize(word.text) for word in words]

    drop = [False] * len(words)
    for i in range(len(words) - min_run + 1):
        if tuple(tokens[i : i + min_run]) in prompt_ngrams:
            drop[i : i + min_run] = [True] * min_run
    return [word for word, dropped in zip(words, drop, strict=True) if not dropped]


def _normalize(token: str) -> str:
    return re.sub(r"[^\w]", "", token.lower())
