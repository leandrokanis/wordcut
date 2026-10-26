"""What the cut suggestion sends to the LLM: the preset's prompt and the sermon's sentences.

Only the sermon goes to the LLM, as numbered sentences without times (constitution §III).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from wordcut.db.transcripts import SentenceRow
from wordcut.service.presets import build_prompt

# Kept out of criteria/texts/base.md, which allows cutting inside a sentence: the answer's
# schema cites whole sentences by number, and base.md changes only by reviewed commit.
ANSWER_FORMAT = """## Formato da resposta

As frases da pregação vêm numeradas, uma por linha, como `N: texto`. Monte cada corte com \
frases inteiras, citadas pelo número; não corte dentro de uma frase.

Responda só com um objeto JSON, sem texto antes ou depois e sem cerca de código, neste esquema:

{"cuts": [{"title": "Título curto do corte", "sentences": [12, 13, 14, 20]}]}

- `title`: título curto do corte, em português, não vazio.
- `sentences`: os números das frases do corte, na ordem em que o corte as toca, sem repetir \
nenhuma.
- Se nenhum trecho servir como corte, responda {"cuts": []}."""


@dataclass(frozen=True)
class SuggestionRequest:
    system: str
    user: str


def build_request(preset: Mapping[str, Any], sentences: Sequence[SentenceRow]) -> SuggestionRequest:
    """The messages of the suggestion for ``preset``, as ``show_preset`` gives it.

    The user message has one line ``N: text`` per sentence, numbered from 1 in sermon order.
    """
    lines = (f"{number}: {sentence.text}" for number, sentence in enumerate(sentences, start=1))
    return SuggestionRequest(
        system=f"{build_prompt(preset)}\n\n{ANSWER_FORMAT}", user="\n".join(lines)
    )
