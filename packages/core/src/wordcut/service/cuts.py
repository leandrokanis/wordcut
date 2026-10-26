"""Cuts of a sermon: list, show and choose them (docs/cli.md §8.1, §8.2, §8.4)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from wordcut.cuts.assembly import AssembledCut, AssembledSegment, assemble
from wordcut.db import cuts, transcripts
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
    return {"items": [_listed(row, assemble(row.segments, words)) for row in in_order]}


def show_cut(connection: sqlite3.Connection, cut_id: int) -> dict[str, Any]:
    """The cut as ``list_cuts`` gives it, plus the time and text of each segment, its words,
    its caption style, its last export options and its exports (docs/cli.md §8.2)."""
    row = _existing(connection, cut_id)
    assembled = assemble(row.segments, transcripts.words_of(connection, row.sermon_id))
    return {
        **_listed(row, assembled),
        "segments": [_segment(segment) for segment in assembled.segments],
        "words": [_word(word) for segment in assembled.segments for word in segment.words],
        # Null in the database means the defaults (items 1.1.f.4 and 1.1.h.1 define them).
        "caption": row.caption or {},
        "render_options": row.render_options or {},
        # Exports arrive with item 1.1.h.1.
        "renders": [],
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


def _with_status(
    connection: sqlite3.Connection, row: CutRow, status: str, now: datetime | None
) -> dict[str, Any]:
    if row.status != status:
        with connection:
            cuts.set_status(connection, row.id, status, now or datetime.now().astimezone())
    return show_cut(connection, row.id)


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


def _word(word: WordRow) -> dict[str, Any]:
    # Spelling fixes (item 1.1.f.2) fill ``corrected``; until then no word has one.
    return {
        "word_id": word.id,
        "text": word.text,
        "start": word.start,
        "end": word.end,
        "corrected": None,
    }


def _existing(connection: sqlite3.Connection, cut_id: int) -> CutRow:
    row = cuts.by_id(connection, cut_id)
    if row is None:
        raise WordcutError("not_found", f"Corte {cut_id} não existe.", {"cut_id": cut_id})
    return row
