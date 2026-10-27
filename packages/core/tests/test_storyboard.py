"""The thumbnail strip from YouTube's storyboards: yt-dlp's JSON written here by hand and
storyboard grids drawn here, served by a double of the download; nothing from YouTube."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from PIL import Image

from wordcut.timeline_media.storyboard import MAX_THUMBNAILS, build_storyboard

LIVE_SECONDS = 100.0


def storyboard_format(
    level: int, width: int, height: int, frames: int, columns: int, rows: int
) -> dict[str, Any]:
    """A storyboard format as yt-dlp lists it (yt_dlp/extractor/youtube/_video.py)."""
    per_grid = columns * rows
    grids = -(-frames // per_grid)
    url = f"https://i.ytimg.com/sb/VIDEO/storyboard3_L{level}/M$M.jpg?sigh=x"
    return {
        "format_id": f"sb{level}",
        "format_note": "storyboard",
        "ext": "mhtml",
        "protocol": "mhtml",
        "width": width,
        "height": height,
        "fps": frames / LIVE_SECONDS,
        "rows": rows,
        "columns": columns,
        "fragments": [
            {"url": url.replace("$M", str(grid)), "duration": LIVE_SECONDS / grids}
            for grid in range(grids)
        ],
    }


def metadata(*formats: dict[str, Any]) -> dict[str, Any]:
    audio = {"format_id": "139", "ext": "m4a", "acodec": "mp4a.40.5", "vcodec": "none"}
    return {"id": "VIDEO", "duration": LIVE_SECONDS, "formats": [audio, *formats]}


class FakeGrids:
    """Draws the grid a fragment URL asks for: each tile filled with a shade that tells its
    frame number, and the last grid only as tall as the rows its frames fill, as YouTube does."""

    def __init__(self, formats: list[dict[str, Any]], frames: dict[str, int]) -> None:
        self._formats = {f["format_id"]: f for f in formats}
        self._frames = frames
        self.fetched: list[str] = []

    def fetch(self, url: str, output: Path) -> Path:
        self.fetched.append(url)
        level = urlparse(url).path.split("/")[3].removeprefix("storyboard3_L")
        grid = int(Path(urlparse(url).path).stem.removeprefix("M"))
        found = self._formats[f"sb{level}"]
        assert parse_qs(urlparse(url).query)["sigh"] == ["x"]
        columns, rows = found["columns"], found["rows"]
        width, height = found["width"], found["height"]
        first = grid * columns * rows
        last = min(first + columns * rows, self._frames[f"sb{level}"])
        filled_rows = -(-(last - first) // columns)
        image = Image.new("RGB", (columns * width, filled_rows * height))
        for frame in range(first, last):
            place = frame - first
            corner = ((place % columns) * width, (place // columns) * height)
            image.paste(shade(frame), (*corner, corner[0] + width, corner[1] + height))
        image.save(output, "JPEG", quality=95)
        return output


def shade(frame: int) -> tuple[int, int, int]:
    return (10 + frame * 10, 255 - frame * 10, 128)


def tile_shade(image: Image.Image, index: int, width: int, height: int) -> tuple[int, ...]:
    pixel = image.getpixel((index * width + width // 2, height // 2))
    assert isinstance(pixel, tuple)
    return pixel


def close(found: tuple[int, ...], expected: tuple[int, int, int]) -> bool:
    return all(abs(a - b) <= 6 for a, b in zip(found, expected, strict=True))


def test_strip_is_built_from_the_largest_storyboard_one_thumbnail_per_frame(
    tmp_path: Path,
) -> None:
    formats = [
        storyboard_format(2, 160, 90, 20, 3, 3),
        storyboard_format(0, 48, 27, 100, 10, 10),
        storyboard_format(1, 80, 45, 50, 5, 5),
    ]
    grids = FakeGrids(formats, {"sb0": 100, "sb1": 50, "sb2": 20})

    strip = build_storyboard(metadata(*formats), grids.fetch, tmp_path)

    assert strip is not None
    with Image.open(strip.image) as image:
        assert image.size == (20 * 160, 90)
        assert all(close(tile_shade(image, i, 160, 90), shade(i)) for i in range(20))
    assert (strip.width, strip.height) == (160, 90)
    assert strip.times == [5.0 * frame for frame in range(20)]


def test_live_without_storyboard_has_no_strip_and_downloads_nothing(tmp_path: Path) -> None:
    grids = FakeGrids([], {})

    assert build_storyboard(metadata(), grids.fetch, tmp_path) is None
    assert grids.fetched == []


def test_long_live_is_shown_by_evenly_spread_thumbnails_up_to_the_limit(tmp_path: Path) -> None:
    frames = 2 * MAX_THUMBNAILS
    formats = [storyboard_format(3, 8, 6, frames, 10, 10)]
    grids = FakeGrids(formats, {"sb3": frames})

    strip = build_storyboard(metadata(*formats), grids.fetch, tmp_path)

    assert strip is not None
    with Image.open(strip.image) as image:
        assert image.size == (MAX_THUMBNAILS * 8, 6)
    seconds_per_frame = LIVE_SECONDS / frames
    assert strip.times == [2 * place * seconds_per_frame for place in range(MAX_THUMBNAILS)]
