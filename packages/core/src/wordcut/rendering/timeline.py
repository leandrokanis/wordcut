"""The timeline of a cut: its segments, cleaned as the export options say."""

from __future__ import annotations

from collections.abc import Sequence

from wordcut.cuts.assembly import AssembledCut
from wordcut.db.transcripts import WordRow
from wordcut.edit.timeline import Energy, Timeline, plan_segments
from wordcut.rendering.options import RenderOptions
from wordcut.transcript import Word


def cut_timeline(
    cut: AssembledCut,
    words: Sequence[WordRow],
    fps: float,
    energy: Energy | None,
    options: RenderOptions,
) -> Timeline:
    """The clips of ``cut`` out of the sermon's ``words`` (in spoken order), with the words'
    original text: the cut's spelling fixes are for the captions only."""
    spoken = [_word(row) for row in words]
    place = {row.id: index for index, row in enumerate(words)}
    segments = [[spoken[place[row.id]] for row in segment.words] for segment in cut.segments]
    return plan_segments(segments, spoken, fps, energy, options.cleanup)


def _word(row: WordRow) -> Word:
    return Word(row.text, row.start, row.end, row.score, row.estimated)
