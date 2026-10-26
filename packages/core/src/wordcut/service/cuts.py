"""Cuts of a sermon: list, show, preview, choose them and fix the spelling of their words
(docs/cli.md §8.1–§8.5)."""

from __future__ import annotations

import sqlite3
import unicodedata
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from wordcut.cuts.assembly import AssembledCut, AssembledSegment, assemble
from wordcut.cuts.spelling import check_spelling
from wordcut.db import cuts, transcripts, word_fixes
from wordcut.db.cuts import CutRow
from wordcut.db.transcripts import WordRow
from wordcut.errors import WordcutError
from wordcut.service.sermons import existing_sermon, shown_cut


def list_cuts(
    connection: sqlite3.Connection, sermon_id: int, status: str | None = None
) -> dict[str, Any]:
    """The cuts of the sermon in the order they were added, the discarded ones last, each
    with what it says and how long it lasts; only those in ``status`` when given
    (docs/cli.md §8.1)."""
    existing_sermon(connection, sermon_id)
    words = transcripts.words_of(connection, sermon_id)
    found = [row for row in cuts.of_sermon(connection, sermon_id) if status in (None, row.status)]
    in_order = sorted(found, key=lambda row: row.status == "discarded")
    fixes = word_fixes.of_sermon(connection, sermon_id)
    return {
        "items": [
            _listed(row, assemble(row.segments, words, fixes.get(row.id, {}))) for row in in_order
        ]
    }


def show_cut(connection: sqlite3.Connection, cut_id: int) -> dict[str, Any]:
    """The cut as ``list_cuts`` gives it, plus the time and text of each segment, its words,
    its caption style, its last export options and its exports (docs/cli.md §8.2)."""
    row = _existing(connection, cut_id)
    assembled = _assembled(connection, row)
    return {
        **_listed(row, assembled),
        "segments": [_segment(segment) for segment in assembled.segments],
        "words": [
            _word(word, segment.fixes) for segment in assembled.segments for word in segment.words
        ],
        # Null in the database means the defaults (items 1.1.f.4 and 1.1.h.1 define them).
        "caption": row.caption or {},
        "render_options": row.render_options or {},
        # Exports arrive with item 1.1.h.1.
        "renders": [],
    }


def preview_cut(connection: sqlite3.Connection, cut_id: int) -> dict[str, Any]:
    """The sequence the preview plays: each segment in the order the cut plays it, with its
    start and end in sermon time, its text and whether it goes back in the sermon, plus the
    duration ``show_cut`` gives (docs/cli.md §8.3). It reads only the database, so the
    processing lock never blocks it (constitution §IV)."""
    row = _existing(connection, cut_id)
    assembled = _assembled(connection, row)
    return {
        "cut_id": row.id,
        "duration": assembled.duration,
        "segments": [
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "out_of_order": out_of_order,
            }
            for segment, out_of_order in zip(
                assembled.segments, assembled.out_of_order, strict=True
            )
        ],
    }


def choose_cut(
    connection: sqlite3.Connection, cut_id: int, now: datetime | None = None
) -> dict[str, Any]:
    """Mark the cut ``chosen`` and give it as ``show_cut`` does; ``now`` defaults to the
    clock. Its content is left as it is (constitution §I), and a cut already chosen is not
    written again."""
    return _with_status(connection, _existing(connection, cut_id), "chosen", now)


def discard_cut(
    connection: sqlite3.Connection, cut_id: int, now: datetime | None = None
) -> dict[str, Any]:
    """Mark the cut ``discarded``, as ``choose_cut`` marks it ``chosen``."""
    return _with_status(connection, _existing(connection, cut_id), "discarded", now)


def restore_cut(
    connection: sqlite3.Connection, cut_id: int, now: datetime | None = None
) -> dict[str, Any]:
    """Bring a discarded cut back to ``suggested``, as ``choose_cut`` marks it ``chosen``.

    A cut that is not discarded is left as it is: restoring undoes a discard only
    (docs/cli.md §8.4).
    """
    row = _existing(connection, cut_id)
    return _with_status(
        connection, row, "suggested" if row.status == "discarded" else row.status, now
    )


def fix_word(
    connection: sqlite3.Connection,
    cut_id: int,
    word_id: int,
    text: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fix the spelling of one word of the cut, in this cut only, and give the word as
    ``show_cut`` does, with the cut; ``now`` defaults to the clock (docs/cli.md §8.5)."""
    row = _existing(connection, cut_id)
    word = _played_word(connection, row, word_id)
    proposed = _one_word(text)
    undo = proposed == unicodedata.normalize("NFC", word.text)
    if not undo:
        _check_spelling(word.text, proposed)
    moment = now or datetime.now().astimezone()
    with connection:
        if undo:
            word_fixes.delete(connection, row.id, word.id)
        else:
            word_fixes.put(connection, row.id, word.id, proposed, moment)
        cuts.mark_edited(connection, row.id, moment)
    return {"cut_id": row.id, **_word(word, word_fixes.of_cut(connection, row.id))}


def _played_word(connection: sqlite3.Connection, row: CutRow, word_id: int) -> WordRow:
    """The word ``word_id`` if one of the cut's segments plays it; its range is not enough."""
    for segment in _assembled(connection, row).segments:
        for word in segment.words:
            if word.id == word_id:
                return word
    raise WordcutError(
        "invalid_argument",
        "A palavra indicada não está em nenhum trecho do corte.",
        {"argument": "word_id"},
    )


def _one_word(text: str) -> str:
    """The typed word without the blanks around it, composed (NFC) like the transcript, so a
    decomposed accent still matches the original word."""
    word = unicodedata.normalize("NFC", text.strip())
    if len(word.split()) != 1:
        raise WordcutError(
            "invalid_argument", "Use uma palavra só na correção.", {"argument": "text"}
        )
    return word


def _check_spelling(original: str, proposed: str) -> None:
    check = check_spelling(original, proposed)
    if not check.accepted:
        raise WordcutError(
            "spelling_too_different",
            f"A correção mudaria o que foi dito: a distância de grafia ({check.distance})"
            f" passa do limite desta palavra ({check.limit}).",
            {"distance": check.distance, "limit": check.limit, "original": original},
        )


def _with_status(
    connection: sqlite3.Connection, row: CutRow, status: str, now: datetime | None
) -> dict[str, Any]:
    if row.status != status:
        with connection:
            cuts.set_status(connection, row.id, status, now or datetime.now().astimezone())
    return show_cut(connection, row.id)


def _assembled(connection: sqlite3.Connection, row: CutRow) -> AssembledCut:
    words = transcripts.words_of(connection, row.sermon_id)
    return assemble(row.segments, words, word_fixes.of_cut(connection, row.id))


def _listed(row: CutRow, assembled: AssembledCut) -> dict[str, Any]:
    """The cut as ``sermon show`` gives it, with its sermon, text and duration."""
    return {
        **shown_cut(row),
        "sermon_id": row.sermon_id,
        "text": assembled.text,
        "duration": assembled.duration,
    }


def _segment(segment: AssembledSegment) -> dict[str, Any]:
    return {
        "from_word": segment.from_word,
        "to_word": segment.to_word,
        "start": segment.start,
        "end": segment.end,
        "text": segment.text,
    }


def _word(word: WordRow, fixes: Mapping[int, str]) -> dict[str, Any]:
    return {
        "word_id": word.id,
        "text": word.text,
        "start": word.start,
        "end": word.end,
        "corrected": fixes.get(word.id),
    }


def _existing(connection: sqlite3.Connection, cut_id: int) -> CutRow:
    row = cuts.by_id(connection, cut_id)
    if row is None:
        raise WordcutError("not_found", f"Corte {cut_id} não existe.", {"cut_id": cut_id})
    return row
