"""Join a timeline's clips into one horizontal montage."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from cortes_pregacao.edit.timeline import Clip

JOIN_FADE_S = 0.015
"""Fade-out then fade-in at every join: removes clicks without overlapping audio,
which would shorten each join and drift lips out of sync."""


def assemble(source: Path, clips: Sequence[Clip], output: Path) -> Path:
    subprocess.run(montage_command(source, clips, output), check=True)
    return output


def montage_command(source: Path, clips: Sequence[Clip], output: Path) -> list[str]:
    """ffmpeg arguments; ``output`` is a near-lossless intermediate (``.mov``).

    Each clip is its own seeked input, so ffmpeg decodes only what is used.
    """
    if not clips:
        raise ValueError("timeline sem clipes")
    inputs: list[str] = []
    chains: list[str] = []
    for index, clip in enumerate(clips):
        inputs += ["-ss", f"{clip.start:.6f}", "-t", f"{clip.duration:.6f}", "-i", str(source)]
        fade_out = max(0.0, clip.duration - JOIN_FADE_S)
        chains.append(
            f"[{index}:v]setpts=PTS-STARTPTS[v{index}];"
            f"[{index}:a]asetpts=PTS-STARTPTS,"
            f"afade=t=in:d={JOIN_FADE_S},afade=t=out:st={fade_out:.6f}:d={JOIN_FADE_S}[a{index}]"
        )
    pairs = "".join(f"[v{i}][a{i}]" for i in range(len(clips)))
    graph = ";".join([*chains, f"{pairs}concat=n={len(clips)}:v=1:a=1[v][a]"])
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs,
        "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-c:a", "pcm_s16le",
        str(output),
    ]  # fmt: skip
