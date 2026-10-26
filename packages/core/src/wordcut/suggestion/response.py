"""The LLM's answer to the cut suggestion, checked against its schema (ADR-0010).

The answer is ``{"cuts": [{"title": str, "sentences": [int, ...]}]}``, with the sentences
numbered as the request numbers them. Nothing is repaired (constitution §III): an answer
outside the schema is ``InvalidResponse``, and the caller asks once more.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


class InvalidResponse(Exception):
    """The answer is outside the schema; the message says why, in Portuguese, for the LLM."""


@dataclass(frozen=True)
class SuggestedCut:
    """A cut as the LLM chose it: ``sentences`` by number, in the order the cut plays them."""

    title: str
    sentences: tuple[int, ...]


def parse_response(text: str, sentence_count: int, *, reorder: bool) -> list[SuggestedCut]:
    """The cuts of the answer ``text`` for a sermon of ``sentence_count`` sentences.

    Without ``reorder``, each cut must play its sentences in sermon order.
    """
    try:
        answer = json.loads(text)
    except json.JSONDecodeError:
        raise InvalidResponse("a resposta não é um JSON válido") from None
    if not isinstance(answer, dict) or not isinstance(answer.get("cuts"), list):
        raise InvalidResponse('a resposta precisa ser um objeto com a lista "cuts"')
    return [
        _cut(number, item, sentence_count, reorder)
        for number, item in enumerate(answer["cuts"], start=1)
    ]


def _cut(number: int, item: Any, sentence_count: int, reorder: bool) -> SuggestedCut:
    if not isinstance(item, dict):
        raise InvalidResponse(f"o corte {number} não é um objeto")
    title = item.get("title")
    if not isinstance(title, str) or not title.strip():
        raise InvalidResponse(f'o corte {number} precisa de um "title" não vazio')
    return SuggestedCut(
        title.strip(), _sentences(number, item.get("sentences"), sentence_count, reorder)
    )


def _sentences(number: int, value: Any, sentence_count: int, reorder: bool) -> tuple[int, ...]:
    if not isinstance(value, list) or not value:
        raise InvalidResponse(f'o corte {number} precisa de uma lista "sentences" não vazia')
    # bool is a subclass of int, and true is not a sentence number.
    if not all(type(sentence) is int for sentence in value):
        raise InvalidResponse(f"o corte {number} tem número de frase que não é inteiro")
    if not all(1 <= sentence <= sentence_count for sentence in value):
        raise InvalidResponse(
            f"o corte {number} cita frase inexistente; as frases vão de 1 a {sentence_count}"
        )
    if len(set(value)) != len(value):
        raise InvalidResponse(f"o corte {number} repete uma frase")
    if not reorder and value != sorted(value):
        raise InvalidResponse(
            f"o corte {number} muda a ordem das frases, e este preset não permite reordenar"
        )
    return tuple(value)
