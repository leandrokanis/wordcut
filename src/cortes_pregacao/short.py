"""A vertical short from a sermon folder and an approved edit list."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from cortes_pregacao.edit.assemble import assemble
from cortes_pregacao.edit.edit_list import EditList
from cortes_pregacao.edit.energy import EnergyProfile
from cortes_pregacao.edit.text import apply_corrections, capitalize
from cortes_pregacao.edit.timeline import Timeline, plan_timeline
from cortes_pregacao.media import video_geometry
from cortes_pregacao.sermon_folder import SermonFolder
from cortes_pregacao.timefmt import format_timestamp
from cortes_pregacao.transcript import Transcript, Word
from cortes_pregacao.vertical.camera import plan_camera
from cortes_pregacao.vertical.captions import DEFAULT_STYLE, CaptionRenderer, build_captions
from cortes_pregacao.vertical.detection import detect_frames
from cortes_pregacao.vertical.render import OUTPUT_WIDTH, render_vertical

IDEAL_DURATION_S = (55.0, 65.0)
ALLOWED_DURATION_S = (40.0, 75.0)


@dataclass(frozen=True)
class ShortPlan:
    edit_list: EditList
    timeline: Timeline
    fps: float

    def warnings(self) -> list[str]:
        problems: list[str] = []
        low, high = ALLOWED_DURATION_S
        if not low <= self.timeline.duration <= high:
            problems.append(
                f"duração {self.timeline.duration:.1f} s fora de {low:.0f}–{high:.0f} s"
            )
        for index in self.edit_list.reordered():
            if not self.edit_list.segments[index].note.strip():
                problems.append(f"trecho {index + 1} fora de ordem sem justificativa")
        return problems


def plan_short(folder: SermonFolder, edit_list: EditList, use_audio: bool = True) -> ShortPlan:
    _, _, fps = video_geometry(folder.sermon_video)
    words = Transcript.load(folder.words).words
    energy = EnergyProfile.from_media(folder.sermon_video) if use_audio else None
    return ShortPlan(edit_list, plan_timeline(edit_list, words, fps, energy), fps)


def preview(plan: ShortPlan) -> str:
    """The roteiro as the approver reads it: segments, cuts and the assembled text."""
    lines = [f'Roteiro: "{plan.edit_list.title}"  ~{plan.timeline.duration:.0f} s', ""]
    reordered = set(plan.edit_list.reordered())
    removed = {(w.start, w.text) for w in plan.timeline.removed}
    for index, segment in enumerate(plan.edit_list.segments):
        arrow = "↑" if index in reordered else " "
        span = f"{format_timestamp(segment.start)}–{format_timestamp(segment.end)}"
        lines.append(f"{index + 1}. {span} {arrow}")
        if segment.note:
            lines.append(f"   └ {segment.note}")
        texts = [
            f"[–{w.text}–]" if (w.start, w.text) in removed else w.text
            for w in _segment_words(plan, index)
        ]
        lines.append("   " + " ".join(texts))
    lines += ["", "Texto montado (como na legenda):", " ".join(w.text for w in caption_words(plan))]
    lines += [f"\n⚠ {problem}" for problem in plan.warnings()]
    return "\n".join(lines)


def caption_words(plan: ShortPlan) -> list[Word]:
    """Output-timed words as shown on screen: corrected, each segment starting in capitals."""
    words: list[Word] = []
    offset, previous_segment = 0.0, None
    for clip in plan.timeline.clips:
        shifted = [word.shifted(offset - clip.start) for word in clip.words]
        if shifted and clip.segment != previous_segment:
            shifted[0] = capitalize(shifted[0])
        words.extend(shifted)
        offset += clip.duration
        previous_segment = clip.segment
    return apply_corrections(words, plan.edit_list.corrections)


def _segment_words(plan: ShortPlan, index: int) -> list[Word]:
    kept = [w for clip in plan.timeline.clips if clip.segment == index for w in clip.words]
    segment = plan.edit_list.segments[index]
    dropped = [w for w in plan.timeline.removed if segment.start <= w.start <= segment.end]
    return sorted([*kept, *dropped], key=lambda w: w.start)


def render_short(folder: SermonFolder, plan: ShortPlan, target: float | None = None) -> Path:
    folder.create()
    work = folder.work / _slug(plan.edit_list.title)
    work.mkdir(parents=True, exist_ok=True)

    _report(f"1/4 montando {len(plan.timeline.clips)} clipes ({plan.timeline.duration:.1f} s)")
    montage = assemble(folder.sermon_video, plan.timeline.clips, work / "montagem.mov", plan.fps)
    width, height, fps = video_geometry(montage)
    if abs(fps - plan.fps) > 0.01:
        raise RuntimeError(f"montagem saiu com {fps:g} fps; a pregação tem {plan.fps:g}")

    _report("2/4 detectando o pregador")
    frames = detect_frames(montage, progress=_progress_bar)
    forced_cuts = [round(t * fps) for t in plan.timeline.segment_starts()]
    camera = plan_camera(frames, width, height, target, forced_cuts)

    _report("3/4 preparando legendas")
    renderer = CaptionRenderer(OUTPUT_WIDTH)
    captions = build_captions(caption_words(plan), renderer.measure)
    images = [renderer.render(caption) for caption in captions]

    _report("4/4 renderizando 1080x1920")
    output = _unique(folder.path / "cortes" / f"corte - {_clean_title(plan.edit_list.title)}.mp4")
    return render_vertical(montage, camera, images, DEFAULT_STYLE.top, fps, output)


def _report(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def _progress_bar(done: int, total: int) -> None:
    if total and (done % 150 == 0 or done == total):
        print(f"   {done}/{total} quadros", file=sys.stderr, flush=True)


def _unique(path: Path) -> Path:
    """``name.mp4``, else ``name-v2.mp4``, ``name-v3.mp4``… — never overwrite."""
    candidate, version = path, 2
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}-v{version}{path.suffix}")
        version += 1
    return candidate


def _clean_title(title: str) -> str:
    return re.sub(r'[/\\:*?"<>|]', "", title).strip()


def _slug(title: str) -> str:
    return re.sub(r"[^\w]+", "-", title.lower()).strip("-") or "corte"
