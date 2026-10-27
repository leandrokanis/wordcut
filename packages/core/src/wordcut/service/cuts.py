"""Cuts of a sermon: list, show, preview, choose them, fix the spelling of their words, set
their caption style, their range and what they play (docs/cli.md §8.1–§8.6, §8.9, §8.10)."""

from __future__ import annotations

import math
import sqlite3
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from wordcut.cuts.assembly import MILLISECOND_DIGITS, AssembledCut, AssembledSegment, assemble
from wordcut.cuts.caption import DEFAULT_CAPTION, stored_caption, validated
from wordcut.cuts.spelling import check_spelling
from wordcut.db import cuts, renders, transcripts, word_fixes
from wordcut.db.cuts import CutRow, Segment
from wordcut.db.renders import RenderRow
from wordcut.db.transcripts import WordRow
from wordcut.edit.cut_range import Span, shift_selection, snap_range, trim_segments
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.processing.sentences import Sentence
from wordcut.rendering.options import merged
from wordcut.service.sermons import existing_sermon, shown_cut

MIN_RANGE_S = 10


def list_cuts(
    connection: sqlite3.Connection, sermon_id: int, status: str | None = None
) -> dict[str, Any]:
    """The cuts of the sermon in the order they were added, the discarded ones last, each
    with what it says, how long it lasts, the stretch of the sermon it spans (``start`` and
    ``end``) and where its range starts and ends (``range_start`` and ``range_end``), in
    sermon time; only those in ``status`` when given (docs/cli.md §8.1)."""
    existing_sermon(connection, sermon_id)
    words = transcripts.words_of(connection, sermon_id)
    found = [row for row in cuts.of_sermon(connection, sermon_id) if status in (None, row.status)]
    in_order = sorted(found, key=lambda row: row.status == "discarded")
    fixes = word_fixes.of_sermon(connection, sermon_id)
    by_id = {word.id: word for word in words}
    return {
        "items": [
            _spanned(row, assemble(row.segments, words, fixes.get(row.id, {})), by_id)
            for row in in_order
        ]
    }


def show_cut(
    connection: sqlite3.Connection, cut_id: int, *, home: Home | None = None
) -> dict[str, Any]:
    """The cut as ``list_cuts`` gives it, plus the time and text of each segment, its words,
    its effective caption style, the options its next export uses and its exports, each with
    its file in ``home`` (by default the one of the environment) (docs/cli.md §8.2)."""
    row = existing_cut(connection, cut_id)
    words = transcripts.words_of(connection, row.sermon_id)
    fixes = word_fixes.of_cut(connection, row.id)
    assembled = assemble(row.segments, words, fixes)
    caption = stored_caption(row.caption)
    return {
        **_listed(row, assembled),
        "segments": [_segment(segment) for segment in assembled.segments],
        "range_sentences": _range_sentences(connection, row, words, fixes),
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


def set_segments(
    connection: sqlite3.Connection,
    cut_id: int,
    segments: Sequence[Mapping[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    """Make ``segments``, ranges of words ``{"from_word", "to_word"}`` in the order the cut
    plays them, what the cut plays, and give it as ``show_cut`` does; ``now`` defaults to
    the clock (docs/cli.md §8.10)."""
    row = existing_cut(connection, cut_id)
    wanted = _valid_segments(connection, row, segments)
    moment = now or datetime.now().astimezone()
    with connection:
        cuts.set_segments(connection, row.id, wanted, moment)
        cuts.mark_edited(connection, row.id, moment)
    return show_cut(connection, row.id)


def set_range(
    connection: sqlite3.Connection,
    cut_id: int,
    start: float | None = None,
    end: float | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Resize the cut's range to ``start`` and ``end`` (sermon time; the one not given stays),
    snapped to the nearest sentence start and end, and drop from what the cut plays the words
    left outside; give the cut as ``show_cut`` does (docs/cli.md §8.9)."""
    if start is None and end is None:
        raise _invalid_range("Informe o início, o fim ou os dois.")
    if not all(math.isfinite(border) for border in (start, end) if border is not None):
        raise _invalid_range("Informe o início e o fim em segundos.")
    row = existing_cut(connection, cut_id)
    spoken = _Spoken.of(connection, row)
    current_start, current_end = spoken.times(row)
    start = current_start if start is None else start
    end = current_end if end is None else end
    if end <= start:
        raise _invalid_range("O fim da faixa precisa vir depois do início.")
    wanted = spoken.checked(snap_range(spoken.sentences, start, end))
    segments = trim_segments(spoken.segments(row), wanted)
    return _store_range(connection, row, spoken, wanted, segments, now)


def move_range(
    connection: sqlite3.Connection, cut_id: int, by: float, now: datetime | None = None
) -> dict[str, Any]:
    """Shift the cut's whole range ``by`` seconds, no further than the sermon, snapped to
    sentences, taking each chosen sentence to the sentence of the new range whose start is
    nearest its own shifted start; give the cut as ``show_cut`` does (docs/cli.md §8.9)."""
    if not math.isfinite(by):
        raise WordcutError(
            "invalid_argument", "Informe o deslocamento em segundos.", {"argument": "by"}
        )
    row = existing_cut(connection, cut_id)
    spoken = _Spoken.of(connection, row)
    wanted, segments = shift_selection(
        spoken.sentences, spoken.segments(row), spoken.times(row), by
    )
    return _store_range(connection, row, spoken, spoken.checked(wanted), segments, now)


def _store_range(
    connection: sqlite3.Connection,
    row: CutRow,
    spoken: _Spoken,
    wanted: Span,
    segments: Sequence[Span],
    now: datetime | None,
) -> dict[str, Any]:
    if not segments:
        raise _invalid_range(
            "Nenhuma frase escolhida ficaria na faixa; o corte não pode ficar vazio."
        )
    moment = now or datetime.now().astimezone()
    with connection:
        cuts.set_range(
            connection,
            row.id,
            spoken.ids(wanted),
            [Segment(*spoken.ids(s)) for s in segments],
            moment,
        )
        cuts.mark_edited(connection, row.id, moment)
    return show_cut(connection, row.id)


class _Spoken:
    """The words and sentences of a cut's sermon, by position, for ``wordcut.edit.cut_range``."""

    def __init__(self, words: Sequence[WordRow], sentences: Sequence[Sentence]) -> None:
        self.words = words
        self.sentences = sentences
        self._place = {word.id: index for index, word in enumerate(words)}

    @classmethod
    def of(cls, connection: sqlite3.Connection, row: CutRow) -> _Spoken:
        words = transcripts.words_of(connection, row.sermon_id)
        place = {word.id: index for index, word in enumerate(words)}
        sentences = [
            Sentence(
                place[sentence.first_word_id],
                place[sentence.last_word_id],
                sentence.start,
                sentence.end,
                sentence.text,
            )
            for sentence in transcripts.sentences_of(connection, row.sermon_id)
        ]
        return cls(words, sentences)

    def segments(self, row: CutRow) -> list[Span]:
        return [(self._place[s.from_word], self._place[s.to_word]) for s in row.segments]

    def times(self, row: CutRow) -> tuple[float, float]:
        """When the cut's range starts and ends, in sermon time."""
        return (
            self.words[self._place[row.range_start_word]].start,
            self.words[self._place[row.range_end_word]].end,
        )

    def checked(self, span: Span) -> Span:
        """``span``, or ``invalid_argument`` when it runs backwards or is too short."""
        first, last = span
        if last < first:
            raise _invalid_range("O fim da faixa precisa vir depois do início.")
        if self.words[last].end - self.words[first].start < MIN_RANGE_S:
            raise _invalid_range(
                f"A faixa precisa ter ao menos {MIN_RANGE_S} s depois de encostar nas frases."
            )
        return span

    def ids(self, span: Span) -> tuple[int, int]:
        return self.words[span[0]].id, self.words[span[1]].id


def _invalid_range(message: str) -> WordcutError:
    return WordcutError("invalid_argument", message, {"argument": "range"})


def _valid_segments(
    connection: sqlite3.Connection, row: CutRow, segments: Sequence[Mapping[str, Any]]
) -> tuple[Segment, ...]:
    """``segments`` as ranges of words of the cut's range that share no word, or
    ``invalid_argument``; no message repeats what was given (ADR-0015)."""
    if not segments:
        raise _invalid_segments("O corte precisa de ao menos um trecho.")
    words = transcripts.words_of(connection, row.sermon_id)
    place = {word.id: index for index, word in enumerate(words)}
    first, last = place[row.range_start_word], place[row.range_end_word]
    wanted = tuple(_segment_of(item) for item in segments)
    played: set[int] = set()
    for segment in wanted:
        if segment.from_word not in place or segment.to_word not in place:
            raise _invalid_segments("Um trecho cita uma palavra que não é desta pregação.")
        start, end = place[segment.from_word], place[segment.to_word]
        if start > end:
            raise _invalid_segments("Um trecho termina antes de começar.")
        if start < first or end > last:
            raise _invalid_segments("Um trecho sai da faixa do corte.")
        spoken = set(range(start, end + 1))
        if spoken & played:
            raise _invalid_segments("Dois trechos tocam a mesma palavra.")
        played |= spoken
    return wanted


def _segment_of(item: object) -> Segment:
    if not isinstance(item, Mapping):
        raise _invalid_segments("Cada trecho é um objeto com from_word e to_word.")
    bounds = (item.get("from_word"), item.get("to_word"))
    if not all(type(bound) is int for bound in bounds):
        raise _invalid_segments("from_word e to_word são IDs de palavra, números inteiros.")
    return Segment(item["from_word"], item["to_word"])


def _invalid_segments(message: str) -> WordcutError:
    return WordcutError("invalid_argument", message, {"argument": "segments"})


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


def _spanned(row: CutRow, assembled: AssembledCut, by_id: Mapping[int, WordRow]) -> dict[str, Any]:
    """The cut as ``_listed`` gives it, with the earliest start and the latest end of its
    segments and the start and end of its range, which the level 2 timeline draws."""
    return {
        **_listed(row, assembled),
        "start": round(min(segment.start for segment in assembled.segments), MILLISECOND_DIGITS),
        "end": round(max(segment.end for segment in assembled.segments), MILLISECOND_DIGITS),
        "range_start": round(by_id[row.range_start_word].start, MILLISECOND_DIGITS),
        "range_end": round(by_id[row.range_end_word].end, MILLISECOND_DIGITS),
    }


def _range_sentences(
    connection: sqlite3.Connection,
    row: CutRow,
    words: Sequence[WordRow],
    fixes: Mapping[int, str],
) -> list[dict[str, Any]]:
    """The sentences of the sermon inside the cut's range, in spoken order, each cut down to
    the range when it crosses its border, with how much of it the cut plays."""
    place = {word.id: index for index, word in enumerate(words)}
    first, last = place[row.range_start_word], place[row.range_end_word]
    played = {
        index
        for segment in row.segments
        for index in range(place[segment.from_word], place[segment.to_word] + 1)
    }
    found = []
    for sentence in transcripts.sentences_of(connection, row.sermon_id):
        start = max(place[sentence.first_word_id], first)
        end = min(place[sentence.last_word_id], last)
        if start <= end:
            found.append(_range_sentence(sentence.id, words[start : end + 1], fixes, played, start))
    return found


def _range_sentence(
    sentence_id: int,
    spoken: Sequence[WordRow],
    fixes: Mapping[int, str],
    played: set[int],
    position: int,
) -> dict[str, Any]:
    inside = sum(index in played for index in range(position, position + len(spoken)))
    return {
        "id": sentence_id,
        "start": spoken[0].start,
        "end": spoken[-1].end,
        "text": " ".join(fixes.get(word.id, word.text) for word in spoken),
        "first_word": spoken[0].id,
        "last_word": spoken[-1].id,
        "included": "none" if inside == 0 else "all" if inside == len(spoken) else "part",
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
