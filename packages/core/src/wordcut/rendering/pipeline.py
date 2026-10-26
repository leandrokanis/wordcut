"""The export of a cut: montage, camera, captions and the vertical encode, through
``RenderGateways``."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Sequence
from dataclasses import replace
from functools import partial
from pathlib import Path

from wordcut.cuts.assembly import MILLISECOND_DIGITS, AssembledCut
from wordcut.cuts.caption import CaptionSettings, to_style
from wordcut.db.transcripts import WordRow
from wordcut.edit.screen import Respell, caption_words
from wordcut.edit.timeline import Timeline
from wordcut.rendering import RenderGateways
from wordcut.rendering.options import RenderOptions
from wordcut.rendering.timeline import cut_timeline
from wordcut.transcript import Word
from wordcut.vertical.camera import plan_camera
from wordcut.vertical.captions import CaptionImage, CaptionRenderer, build_captions
from wordcut.vertical.render import Encoding

# x264 CRF of each quality (docs/cli.md §8.7).
QUALITY_CRF = {"high": 18, "small": 26}
# Each stage starts at this fraction of the export; detection, the slowest before the encode,
# moves through its share frame by frame.
ASSEMBLING = (0.0, "montando")
DETECTING = (0.1, "detectando o pregador")
CAPTIONING = (0.6, "preparando legendas")
RENDERING = (0.65, "renderizando")
MONTAGE_FILE = "montage.mov"
RENDER_FILE = "render.mp4"

Progress = Callable[[float, str], None]
"""Called with how far the export is, from 0 to 1, and what it is doing, in Portuguese."""


def render_cut(
    gateways: RenderGateways,
    video: Path,
    words: Sequence[WordRow],
    cut: AssembledCut,
    caption: CaptionSettings,
    options: RenderOptions,
    workdir: Path,
    output: Path,
    progress: Progress,
) -> float:
    """Export ``cut`` of the sermon ``video`` (whose words are ``words``) to ``output`` and give
    its duration in seconds. Scratch files go in ``workdir``, which is removed at the end;
    ``output`` appears only once the export succeeded."""
    workdir.mkdir(parents=True)
    try:
        progress(*ASSEMBLING)
        width, height, fps = gateways.geometry(video)
        timeline = cut_timeline(cut, words, fps, gateways.energy(video), options)
        montage = gateways.assemble(
            video, timeline.clips, workdir / MONTAGE_FILE, fps, smooth_joins=options.smooth_joins
        )
        progress(*DETECTING)
        frames = gateways.detect(montage, partial(_detecting, progress))
        jumps = [round(start * fps) for start in timeline.segment_starts()]
        camera = plan_camera(frames, width, height, forced_cuts=jumps)
        progress(*CAPTIONING)
        encoding = _encoding(options)
        captions = _captions(timeline, cut, caption, encoding)
        progress(*RENDERING)
        rendered = gateways.render(montage, camera, captions, fps, workdir / RENDER_FILE, encoding)
        os.replace(rendered, output)
        return round(timeline.duration, MILLISECOND_DIGITS)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _captions(
    timeline: Timeline, cut: AssembledCut, caption: CaptionSettings, encoding: Encoding
) -> list[CaptionImage]:
    if not caption.enabled:
        return []
    renderer = CaptionRenderer(encoding.width, to_style(caption, encoding.height))
    words = caption_words(timeline, _fixed_spelling(cut))
    return [
        renderer.render(block) for block in build_captions(words, renderer.measure, renderer.style)
    ]


def _fixed_spelling(cut: AssembledCut) -> Respell:
    """Spell each word as the cut fixed it. The timeline's words are the transcript's, which
    the cleanup may have re-punctuated, so a word is known by its times, not by its text."""
    fixes = {
        (row.start, row.end): segment.fixes[row.id]
        for segment in cut.segments
        for row in segment.words
        if row.id in segment.fixes
    }

    def respell(words: Sequence[Word]) -> list[Word]:
        return [
            replace(word, text=fixes[word.start, word.end])
            if (word.start, word.end) in fixes
            else word
            for word in words
        ]

    return respell


def _encoding(options: RenderOptions) -> Encoding:
    width, height = (int(side) for side in options.resolution.split("x"))
    return Encoding(
        width,
        height,
        crf=QUALITY_CRF[options.quality],
        normalize=options.normalize,
        fade=options.fade,
    )


def _detecting(progress: Progress, done: int, total: int) -> None:
    start, message = DETECTING
    share = CAPTIONING[0] - start
    progress(start + share * min(done / total, 1.0) if total else start, message)
