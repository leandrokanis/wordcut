"""How long an export will last, without opening any media (FR-009)."""

from __future__ import annotations

from collections.abc import Sequence

from wordcut.cuts.assembly import MILLISECOND_DIGITS, AssembledCut
from wordcut.db.transcripts import WordRow
from wordcut.rendering.options import RenderOptions
from wordcut.rendering.timeline import cut_timeline

# The database does not keep the sermon's frame rate, and reading it would open the video;
# cut points snap to frames of this rate instead, at most half a frame from the real ones.
NOMINAL_FRAME_RATE = 30.0


def estimated_duration(
    cut: AssembledCut, words: Sequence[WordRow], options: RenderOptions
) -> float:
    """The duration of the cut's timeline with ``options``, in seconds, without the audio's
    loudness, which only moves cut points among nearby frames."""
    timeline = cut_timeline(cut, words, NOMINAL_FRAME_RATE, None, options)
    return round(timeline.duration, MILLISECOND_DIGITS)
