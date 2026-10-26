from dataclasses import replace

from wordcut.cuts.assembly import assemble
from wordcut.db.cuts import Segment
from wordcut.db.transcripts import WordRow
from wordcut.edit.timeline import Cleanup, plan_segments
from wordcut.rendering.estimate import NOMINAL_FRAME_RATE, estimated_duration
from wordcut.rendering.options import RenderOptions
from wordcut.transcript import Word

# A long pause inside a sentence and a filler ("hã").
WORDS = tuple(
    WordRow(id=10 + position, position=position, text=text, start=start, end=end,
            score=None, estimated=False)
    for position, (text, start, end) in enumerate(
        [("Irmãos,", 1.0, 1.4), ("hã", 1.5, 1.8), ("Deus", 1.9, 2.3), ("reina.", 4.0, 4.5)]
    )
)  # fmt: skip
CUT = assemble((Segment(10, 13),), WORDS, {})


def test_the_estimate_shortens_with_short_pauses_and_grows_when_fillers_stay() -> None:
    natural = estimated_duration(CUT, WORDS, RenderOptions())
    short = estimated_duration(CUT, WORDS, replace(RenderOptions(), pauses="short"))
    with_fillers = estimated_duration(CUT, WORDS, replace(RenderOptions(), fillers="keep"))

    assert (short < natural < with_fillers) is True


def test_the_estimate_is_the_timeline_at_the_nominal_rate_without_audio_loudness() -> None:
    spoken = [Word(row.text, row.start, row.end) for row in WORDS]

    planned = plan_segments([spoken], spoken, NOMINAL_FRAME_RATE, None, Cleanup(pauses="short"))

    assert estimated_duration(CUT, WORDS, replace(RenderOptions(), pauses="short")) == round(
        planned.duration, 3
    )
