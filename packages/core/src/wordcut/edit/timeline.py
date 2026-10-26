"""From the segments of a cut to the exact source intervals ("clips") it plays.

Within each segment, hesitations are cut out and silences are shortened:
pauses after a sentence end keep up to ``RHETORICAL_PAUSE_S`` (the preacher's
breath before the next idea); any other pause keeps ``PAUSE_S``. Every cut
point lands on a video frame boundary — so audio and video stay in sync
through dozens of joins — and, among nearby frames, on the quietest one.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from wordcut.edit.cleanup import remove_hesitations
from wordcut.transcript import Word

PAUSE_S = 0.15
RHETORICAL_PAUSE_S = 0.40
SHORT_PAUSE_S = 0.08
SHORT_RHETORICAL_PAUSE_S = 0.20
EDGE_PAD_S = 0.08
SNAP_FRAMES = 2
SENTENCE_END = (".", "?", "!")

Energy = Callable[[float], float]
"""Audio loudness around a source time; lower is quieter."""


@dataclass(frozen=True)
class PauseLimits:
    """The longest pause kept between two words of a segment, in seconds: after a sentence
    end, and anywhere else."""

    after_sentence: float
    within_sentence: float


# docs/cli.md §8.7: "original" never shortens a pause between words of the same segment.
PAUSES: dict[str, PauseLimits] = {
    "original": PauseLimits(math.inf, math.inf),
    "natural": PauseLimits(RHETORICAL_PAUSE_S, PAUSE_S),
    "short": PauseLimits(SHORT_RHETORICAL_PAUSE_S, SHORT_PAUSE_S),
}


@dataclass(frozen=True)
class Cleanup:
    """What the timeline removes: fillers, stammers and how much of each pause."""

    fillers: bool = True
    stammers: bool = True
    pauses: str = "natural"

    @property
    def limits(self) -> PauseLimits:
        return PAUSES[self.pauses]


DEFAULT_CLEANUP = Cleanup()


@dataclass(frozen=True)
class Clip:
    start: float
    end: float
    words: tuple[Word, ...]
    segment: int

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class Timeline:
    clips: tuple[Clip, ...]
    removed: tuple[Word, ...]

    @property
    def duration(self) -> float:
        return sum(clip.duration for clip in self.clips)

    def output_words(self) -> list[Word]:
        """Kept words with times on the short's own clock."""
        words: list[Word] = []
        offset = 0.0
        for clip in self.clips:
            words.extend(word.shifted(offset - clip.start) for word in clip.words)
            offset += clip.duration
        return words

    def segment_starts(self) -> list[float]:
        """Output times where a new segment begins (excluding 0)."""
        starts: list[float] = []
        offset = 0.0
        for previous, clip in zip(self.clips, self.clips[1:], strict=False):
            offset += previous.duration
            if clip.segment != previous.segment:
                starts.append(offset)
        return starts


def plan_segments(
    segments: Sequence[Sequence[Word]],
    words: Sequence[Word],
    fps: float,
    energy: Energy | None = None,
    cleanup: Cleanup = DEFAULT_CLEANUP,
) -> Timeline:
    """The clips of ``segments``, each given by its words in spoken order, in the order they
    play; ``words`` are all the words of the source, which the cuts must not reach into."""
    starts = [word.start for word in words]
    clips: list[Clip] = []
    removed: list[Word] = []
    limits = cleanup.limits
    for index, inside in enumerate(segments):
        cleaned = remove_hesitations(inside, fillers=cleanup.fillers, stammers=cleanup.stammers)
        removed.extend(cleaned.removed)
        for run in _runs(cleaned.kept, set(cleaned.removed), limits):
            clips.append(_clip(run, index, words, starts, fps, energy, limits))
    return Timeline(tuple(clips), tuple(removed))


def _runs(kept: Sequence[Word], removed: set[Word], limits: PauseLimits) -> list[list[Word]]:
    """Split kept words wherever audio must be cut: a removed word or a long pause."""
    runs: list[list[Word]] = []
    removed_starts = sorted(word.start for word in removed)
    for word in kept:
        if runs and not _must_cut(runs[-1][-1], word, removed_starts, limits):
            runs[-1].append(word)
        else:
            runs.append([word])
    return runs


def _must_cut(before: Word, after: Word, removed_starts: list[float], limits: PauseLimits) -> bool:
    between = bisect.bisect_left(removed_starts, before.end) < bisect.bisect_left(
        removed_starts, after.start
    )
    return between or after.start - before.end > _allowed_pause(before, limits)


def _allowed_pause(word: Word, limits: PauseLimits) -> float:
    if word.text.endswith(SENTENCE_END):
        return limits.after_sentence
    return limits.within_sentence


def _clip(
    run: list[Word],
    segment: int,
    words: Sequence[Word],
    starts: list[float],
    fps: float,
    energy: Energy | None,
    limits: PauseLimits,
) -> Clip:
    first, last = run[0], run[-1]
    position = bisect.bisect_left(starts, first.start)
    previous_end = words[position - 1].end if position > 0 else 0.0
    following = bisect.bisect_right(starts, last.start)
    next_start = words[following].start if following < len(words) else last.end + EDGE_PAD_S

    space_before = max(0.0, first.start - previous_end)
    space_after = max(0.0, next_start - last.end)
    # Half of the allowed pause on each side of a cut, never reaching into a neighbour.
    lead = min(
        _allowed_pause(words[position - 1], limits) / 2 if position else EDGE_PAD_S,
        space_before / 2,
    )
    tail = min(_allowed_pause(last, limits) / 2, space_after / 2)

    start = _snap(first.start - lead, first.start - space_before / 2, first.start, fps, energy)
    end = _snap(last.end + tail, last.end, last.end + space_after / 2, fps, energy)
    if end <= start:
        end = start + 1 / fps
    return Clip(start, end, tuple(run), segment)


def _snap(target: float, low: float, high: float, fps: float, energy: Energy | None) -> float:
    """Nearest-quietest frame boundary to ``target`` within ``[low, high]``."""
    nearest = round(target * fps)
    candidates = [
        frame / fps
        for frame in range(nearest - SNAP_FRAMES, nearest + SNAP_FRAMES + 1)
        if low <= frame / fps <= high
    ]
    if not candidates:
        return nearest / fps
    if energy is None:
        return min(candidates, key=lambda t: abs(t - target))
    return min(candidates, key=lambda t: (energy(t), abs(t - target)))
