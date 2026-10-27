"""The thumbnail strip of a live, made from YouTube's storyboards as yt-dlp lists them.

yt-dlp lists each storyboard as a format ``sbN`` (yt_dlp/extractor/youtube/_video.py,
``_extract_storyboard``): ``width`` and ``height`` of one thumbnail, ``columns`` and ``rows``
of each grid image, ``fps`` of thumbnails per second of the live, and ``fragments``, the
URLs of the grid images in order. The strip lays the thumbnails side by side, in time order.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

STRIP_FILE = "thumbnails.jpg"
STRIP_QUALITY = 80
# More thumbnails than a wide screen shows; also keeps the strip within JPEG's 65535 px.
MAX_THUMBNAILS = 240
STORYBOARD_NOTE = "storyboard"

# Downloads the file at a URL to a path and returns the path.
Fetch = Callable[[str, Path], Path]


@dataclass(frozen=True)
class Storyboard:
    """The strip ``image`` of thumbnails of ``width`` by ``height`` pixels, side by side, and
    the second of the live each one shows."""

    image: Path
    width: int
    height: int
    times: list[float]


@dataclass(frozen=True)
class _Format:
    width: int
    height: int
    columns: int
    rows: int
    frames: int
    grids: list[str]

    @property
    def per_grid(self) -> int:
        return self.columns * self.rows


def build_storyboard(metadata: dict[str, Any], fetch: Fetch, out_dir: Path) -> Storyboard | None:
    """The strip of the live yt-dlp's ``metadata`` describes, from its largest storyboard,
    with its grid images downloaded by ``fetch``; ``None`` when the live has no storyboard."""
    chosen = _largest_format(metadata)
    if chosen is None:
        return None
    duration = float(metadata["duration"])
    shown = _sampled_frames(chosen.frames)
    out_dir.mkdir(parents=True, exist_ok=True)
    grids = _fetched_grids(chosen, shown, fetch, out_dir)
    strip = Image.new("RGB", (len(shown) * chosen.width, chosen.height))
    for place, frame in enumerate(shown):
        strip.paste(_thumbnail(chosen, grids, frame), (place * chosen.width, 0))
    image = out_dir / STRIP_FILE
    strip.save(image, "JPEG", quality=STRIP_QUALITY)
    seconds_per_frame = duration / chosen.frames
    return Storyboard(
        image=image,
        width=chosen.width,
        height=chosen.height,
        times=[frame * seconds_per_frame for frame in shown],
    )


def _largest_format(metadata: dict[str, Any]) -> _Format | None:
    duration = metadata.get("duration")
    candidates = [
        found
        for found in metadata.get("formats") or []
        if found.get("format_note") == STORYBOARD_NOTE and found.get("fragments")
    ]
    if not candidates or not duration:
        return None
    largest = max(candidates, key=lambda found: found["width"] * found["height"])
    grids = [fragment["url"] for fragment in largest["fragments"]]
    per_grid = largest["columns"] * largest["rows"]
    frames = min(round(largest["fps"] * duration), len(grids) * per_grid)
    return _Format(
        width=largest["width"],
        height=largest["height"],
        columns=largest["columns"],
        rows=largest["rows"],
        frames=frames,
        grids=grids,
    )


def _sampled_frames(frames: int) -> list[int]:
    """The frames the strip shows: all of them, or ``MAX_THUMBNAILS`` evenly spread."""
    count = min(frames, MAX_THUMBNAILS)
    return [math.floor(place * frames / count) for place in range(count)]


def _fetched_grids(
    chosen: _Format, shown: list[int], fetch: Fetch, out_dir: Path
) -> dict[int, Image.Image]:
    needed = sorted({frame // chosen.per_grid for frame in shown})
    grids: dict[int, Image.Image] = {}
    for grid in needed:
        path = fetch(chosen.grids[grid], out_dir / f"grid-{grid}.jpg")
        with Image.open(path) as opened:
            grids[grid] = opened.convert("RGB")
    return grids


def _thumbnail(chosen: _Format, grids: dict[int, Image.Image], frame: int) -> Image.Image:
    grid, place = divmod(frame, chosen.per_grid)
    row, column = divmod(place, chosen.columns)
    left, top = column * chosen.width, row * chosen.height
    return grids[grid].crop((left, top, left + chosen.width, top + chosen.height))
