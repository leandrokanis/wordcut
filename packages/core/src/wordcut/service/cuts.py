"""Cuts of a sermon: list, show, preview, choose them, fix the spelling of their words and
set their caption style (docs/cli.md §8.1–§8.6)."""

from __future__ import annotations

import sqlite3
import unicodedata
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from wordcut.cuts.assembly import MILLISECOND_DIGITS, AssembledCut, AssembledSegment, assemble
from wordcut.cuts.caption import DEFAULT_CAPTION, stored_caption, validated
from wordcut.cuts.spelling import check_spelling
from wordcut.db import cuts, renders, transcripts, word_fixes
from wordcut.db.cuts import CutRow
from wordcut.db.renders import RenderRow
from wordcut.db.transcripts import WordRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.rendering.options import merged
from wordcut.service.sermons import existing_sermon, shown_cut


def list_cuts(
    connection: sqlite3.Connection, sermon_id: int, status: str | None = None
) -> dict[str, Any]:
    """The cuts of the sermon in the order they were added, the discarded ones last, each
    with what it says, how long it lasts and the stretch of the sermon it spans (``start``
    and ``end``, in sermon time); only those in ``status`` when given (docs/cli.md §8.1)."""
    existing_sermon(connection, sermon_id)
    words = transcripts.words_of(connection, sermon_id)
    found = [row for row in cuts.of_sermon(connection, sermon_id) if status in (None, row.status)]
    in_order = sorted(found, key=lambda row: row.status == "discarded")
    fixes = word_fixes.of_sermon(connection, sermon_id)
    return {
        "items": [
            _spanned(row, assemble(row.segments, words, fixes.get(row.id, {}))) for row in in_order
        ]
    }


def show_cut(
    connection: sqlite3.Connection, cut_id: int, *, home: Home | None = None
) -> dict[str, Any]:
    """The cut as ``list_cuts`` gives it, plus the time and text of each segment, its words,
    its effective caption style, the options its next export uses and its exports, each with
    its file in ``home`` (by default the one of the environment) (docs/cli.md §8.2)."""
    row = existing_cut(connection, cut_id)
    assembled = _assembled(connection, row)
    caption = stored_caption(row.caption)
    return {
        **_listed(row, assembled),
        "segments": [_segment(segment) for segment in assembled.segments],
        "words": [
            _word(word, segment.fixes) for segment in assembled.segments for word in segment.words
        ],
        "caption": caption.as_dict(),
        "render_options": merged(row.render_options, {}).summary(caption=caption.enabled),
        "renders": _renders(connection, row.id, home),
    }


def preview_cut(connection: sqlite3.Connection, cut_id: int) -> dict[str, Any]:
    """The sequence the preview plays: each segment in the order the cut plays it, with its
    start and end in sermon time, its text and whether it goes back in the sermon, plus the
    duration ``show_cut`` gives (docs/cli.md §8.3). It reads only the database, so the
    processing lock never blocks it (constitution §IV)."""
    row = existing_cut(connection, cut_id)
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
    return _with_status(connection, existing_cut(connection, cut_id), "chosen", now)


def discard_cut(
    connection: sqlite3.Connection, cut_id: int, now: datetime | None = None
) -> dict[str, Any]:
    """Mark the cut ``discarded``, as ``choose_cut`` marks it ``chosen``."""
    return _with_status(connection, existing_cut(connection, cut_id), "discarded", now)


def restore_cut(
    connection: sqlite3.Connection, cut_id: int, now: datetime | None = None
) -> dict[str, Any]:
    """Bring a discarded cut back to ``suggested``, as ``choose_cut`` marks it ``chosen``.

    A cut that is not discarded is left as it is: restoring undoes a discard only
    (docs/cli.md §8.4).
    """
    row = existing_cut(connection, cut_id)
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
    row = existing_cut(connection, cut_id)
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


def caption_of(connection: sqlite3.Connection, cut_id: int) -> dict[str, Any]:
    """The caption style of the cut, the default when it has none (docs/cli.md §8.6)."""
    return stored_caption(existing_cut(connection, cut_id).caption).as_dict()


def update_caption(
    connection: sqlite3.Connection,
    cut_id: int,
    changes: Mapping[str, Any],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Change only the given fields of the cut's caption style and give the whole style;
    ``now`` defaults to the clock. The cut becomes edited; a refused change stores nothing
    (docs/cli.md §8.6)."""
    row = existing_cut(connection, cut_id)
    style = validated(stored_caption(row.caption), changes).as_dict()
    _store_caption(connection, row.id, style, now)
    return style


def reset_caption(
    connection: sqlite3.Connection, cut_id: int, now: datetime | None = None
) -> dict[str, Any]:
    """Bring the cut's caption back to the default, turned on, as ``update_caption`` changes
    it; nothing is stored, so the cut follows the default even if it changes."""
    row = existing_cut(connection, cut_id)
    _store_caption(connection, row.id, None, now)
    return DEFAULT_CAPTION.as_dict()


def _store_caption(
    connection: sqlite3.Connection, cut_id: int, style: dict[str, Any] | None, now: datetime | None
) -> None:
    """Store the style and mark the cut edited, so ``sermon suggest`` keeps it (§7.6)."""
    moment = now or datetime.now().astimezone()
    with connection:
        cuts.set_caption(connection, cut_id, style, moment)
        cuts.mark_edited(connection, cut_id, moment)


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


def _spanned(row: CutRow, assembled: AssembledCut) -> dict[str, Any]:
    """The cut as ``_listed`` gives it, with the earliest start and the latest end of its
    segments: the stretch of the sermon the level 2 timeline draws it over."""
    return {
        **_listed(row, assembled),
        "start": round(min(segment.start for segment in assembled.segments), MILLISECOND_DIGITS),
        "end": round(max(segment.end for segment in assembled.segments), MILLISECOND_DIGITS),
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


def existing_cut(connection: sqlite3.Connection, cut_id: int) -> CutRow:
    """The cut, or ``not_found`` when there is none with ``cut_id``."""
    row = cuts.by_id(connection, cut_id)
    if row is None:
        raise WordcutError("not_found", f"Corte {cut_id} não existe.", {"cut_id": cut_id})
    return row


def _renders(
    connection: sqlite3.Connection, cut_id: int, home: Home | None
) -> list[dict[str, Any]]:
    found = renders.of_cut(connection, cut_id)
    if not found:
        return []
    where = home or Home.from_environment()
    return [shown_render(row, where) for row in found]


def shown_render(row: RenderRow, home: Home) -> dict[str, Any]:
    """The export as ``render show`` gives it, its ``path`` the local file (docs/cli.md §9)."""
    return {
        "id": row.id,
        "cut_id": row.cut_id,
        "path": str((home.root / row.path).absolute()),
        "duration": row.duration,
        "created_at": row.created_at.isoformat(),
        "options": row.options,
    }
