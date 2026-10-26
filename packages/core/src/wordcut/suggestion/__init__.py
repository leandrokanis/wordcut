"""The cut suggestion: the LLM picks the cuts of a processed sermon (2.1.b.1, ADR-0010).

``suggest`` sends the preset's prompt and the numbered sentences to the model that
``default_model`` builds from the settings, and saves the cuts of a valid answer as
``suggested``. Tests replace ``default_model``; the suite makes the real one fail.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from wordcut import config, network
from wordcut.db import cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import SuggestionError
from wordcut.db.transcripts import SentenceRow
from wordcut.errors import WordcutError
from wordcut.service.sermons import processed_row
from wordcut.service.settings import llm_model
from wordcut.suggestion.model import OpenRouterModel, SuggestionModel
from wordcut.suggestion.request import SuggestionRequest, build_request
from wordcut.suggestion.response import InvalidResponse, SuggestedCut, parse_response

__all__ = [
    "SuggestionModel",
    "SuggestionResult",
    "default_model",
    "require_configured",
    "suggest",
]

# What to run for each setting the suggestion lacks (docs/cli.md §11.1).
MISSING_SETTINGS = {
    "llm_model": "o modelo do LLM (wordcut settings set --model <id>)",
    "llm_key": "a chave do LLM (wordcut settings set-key)",
}

# criteria/texts/base.md: cleaning hesitations and pauses takes 15-20% of the raw time; 18% here.
CLEANED_SHARE = 0.82
# Durations are kept to the millisecond, so a bound is reached exactly (docs/cli.md §2).
MILLISECOND_DIGITS = 3

# Constitution §III: one more try, with the same messages and what was wrong; no repair.
RETRY_NOTE = (
    "A resposta anterior foi recusada: {reason}. Responda de novo só com o objeto JSON,"
    " no esquema pedido."
)


def default_model(llm_model: str, key: str) -> SuggestionModel:
    """The real LLM: ``llm_model`` on OpenRouter, called with ``key``; refused with
    ``network_error`` while the network is forbidden (ADR-0017)."""
    network.refuse_when_forbidden("o OpenRouter")
    return OpenRouterModel(llm_model, key)


@dataclass(frozen=True)
class SuggestionResult:
    """The IDs of the cuts a suggestion saved, and a warning for each cut it dropped."""

    cut_ids: tuple[int, ...]
    warnings: tuple[dict[str, Any], ...]

    @property
    def saved(self) -> int:
        return len(self.cut_ids)


def suggest(
    connection: sqlite3.Connection,
    sermon_id: int,
    preset: Mapping[str, Any],
    *,
    replace_suggested: bool = False,
) -> SuggestionResult:
    """Ask the LLM for the cuts of the processed sermon with ``preset``, as ``show_preset``
    gives it, and save them as ``suggested``.

    A cut whose estimated duration falls outside the preset's allowed one is dropped with a
    warning ``{"title", "estimated_duration", "message"}``. A failure is kept on the sermon as
    its ``suggestion_error`` and raised as ``WordcutError``; a success clears it. With
    ``replace_suggested``, a success also removes, in the same transaction, the ``suggested``
    cuts nobody has edited (2.1.b.2).
    """
    processed_at = processed_row(connection, sermon_id).processed_at if replace_suggested else None
    try:
        chosen, sentences = _suggested(connection, sermon_id, preset)
    except WordcutError as error:
        with connection:
            sermons.record_suggestion_error(
                connection, sermon_id, SuggestionError(error.code, error.message)
            )
        raise
    kept, warnings = _within_duration(chosen, sentences, preset)
    with connection:
        if replace_suggested:
            cuts.delete_unedited_suggestions(connection, sermon_id)
            # Checked after the delete, which opens the write transaction: a reprocessing cannot
            # commit between the check and the insert. The cuts' word IDs have no foreign key.
            _require_processed_at(connection, sermon_id, processed_at)
        saved = cuts.insert_many(connection, sermon_id, kept, datetime.now().astimezone())
        sermons.record_suggestion_error(connection, sermon_id, None)
    return SuggestionResult(cut_ids=tuple(saved), warnings=tuple(warnings))


def _require_processed_at(
    connection: sqlite3.Connection, sermon_id: int, processed_at: datetime | None
) -> None:
    """Refuse the cuts when the sermon was processed again, or is being processed, since the
    suggestion started: they point to words that may be gone."""
    row = sermons.by_id(connection, sermon_id)
    if row is None or row.status != "processed" or row.processed_at != processed_at:
        raise WordcutError(
            "sermon_not_processed",
            f"A pregação {sermon_id} foi processada de novo durante a sugestão;"
            " nenhum corte foi gravado.",
            {"sermon_id": sermon_id, "status": None if row is None else row.status},
        )


def _suggested(
    connection: sqlite3.Connection, sermon_id: int, preset: Mapping[str, Any]
) -> tuple[list[SuggestedCut], list[SentenceRow]]:
    model = _configured_model(connection)
    sentences = transcripts.sentences_of(connection, sermon_id)
    chosen = _asked(model, build_request(preset, sentences), len(sentences), preset["reorder"])
    return chosen, sentences


def _asked(
    model: SuggestionModel, request: SuggestionRequest, sentence_count: int, reorder: bool
) -> list[SuggestedCut]:
    """The cuts of the model's answer, asked once more when the first is outside the schema."""

    def answer(user: str) -> list[SuggestedCut]:
        return parse_response(model.complete(request.system, user), sentence_count, reorder=reorder)

    try:
        return answer(request.user)
    except InvalidResponse as refused:
        retry = f"{request.user}\n\n{RETRY_NOTE.format(reason=refused)}"
    try:
        return answer(retry)
    except InvalidResponse as refused_again:
        raise WordcutError(
            "llm_error",
            "O LLM respondeu fora do formato pedido duas vezes; nenhum corte foi sugerido.",
            {"reason": str(refused_again)},
        ) from None


def require_configured(connection: sqlite3.Connection) -> tuple[str, str]:
    """The LLM model and key of the settings, or ``llm_not_configured`` naming what is
    missing; the message never carries the key."""
    name, key = llm_model(connection), config.llm_key()
    if name is None or key is None:
        missing = [
            setting for setting, value in (("llm_model", name), ("llm_key", key)) if value is None
        ]
        raise WordcutError(
            "llm_not_configured",
            "Sem "
            + " e sem ".join(MISSING_SETTINGS[setting] for setting in missing)
            + "; nenhum corte foi sugerido.",
            {"missing": missing},
        )
    return name, key


def _configured_model(connection: sqlite3.Connection) -> SuggestionModel:
    return default_model(*require_configured(connection))


def _new_cut(cut: SuggestedCut, sentences: Sequence[SentenceRow], preset_id: int) -> NewCut:
    chosen = [sentences[number - 1] for number in cut.sentences]
    in_sermon_order = sorted(chosen, key=lambda row: row.position)
    return NewCut(
        status="suggested",
        title=cut.title,
        segments=tuple(_segments(cut.sentences, sentences)),
        range_start_word=in_sermon_order[0].first_word_id,
        range_end_word=in_sermon_order[-1].last_word_id,
        source="llm",
        preset_id=preset_id,
    )


def _within_duration(
    chosen: Sequence[SuggestedCut], sentences: Sequence[SentenceRow], preset: Mapping[str, Any]
) -> tuple[list[NewCut], list[dict[str, Any]]]:
    """The cuts that last the preset's allowed duration once cleaned, and a warning for each
    of the others; both bounds are allowed."""
    allowed = preset["duration_allowed"]
    kept: list[NewCut] = []
    warnings: list[dict[str, Any]] = []
    for cut in chosen:
        estimated = _estimated_duration(cut, sentences)
        if allowed["min"] <= estimated <= allowed["max"]:
            kept.append(_new_cut(cut, sentences, preset["id"]))
        else:
            warnings.append(_dropped(cut, estimated, allowed))
    return kept, warnings


def _estimated_duration(cut: SuggestedCut, sentences: Sequence[SentenceRow]) -> float:
    """Seconds the cut lasts once cleaned: each segment from its first word's start to its last
    word's end (sermon time), summed, less the cleanup's share."""
    raw = sum(
        sentences[run[-1] - 1].end - sentences[run[0] - 1].start for run in _runs(cut.sentences)
    )
    return round(raw * CLEANED_SHARE, MILLISECOND_DIGITS)


def _dropped(cut: SuggestedCut, estimated: float, allowed: Mapping[str, int]) -> dict[str, Any]:
    return {
        "title": cut.title,
        "estimated_duration": estimated,
        "message": (
            f'Corte "{cut.title}" descartado: duração estimada de {estimated:.0f} s,'
            f" fora de {allowed['min']}–{allowed['max']} s."
        ),
    }


def _segments(numbers: Sequence[int], sentences: Sequence[SentenceRow]) -> list[Segment]:
    """One segment per run of consecutive sentences, in the order the cut plays them."""
    return [
        Segment(sentences[run[0] - 1].first_word_id, sentences[run[-1] - 1].last_word_id)
        for run in _runs(numbers)
    ]


def _runs(numbers: Sequence[int]) -> list[list[int]]:
    """``numbers`` split where one is not the previous plus one: ``[3, 4, 9]`` → ``[3, 4], [9]``."""
    runs: list[list[int]] = []
    for number in numbers:
        if runs and number == runs[-1][-1] + 1:
            runs[-1].append(number)
        else:
            runs.append([number])
    return runs
