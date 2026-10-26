"""The fonts shipped in the package, by the name their files declare ("Open Sans Bold")."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from PIL import ImageFont

FONTS_DIR = Path(__file__).resolve().parents[1] / "assets/fonts"
FONT_SUFFIXES = (".ttf", ".otf")


def available_fonts() -> dict[str, Path]:
    """Each packaged font file by its family and style name, sorted by name."""
    return dict(_catalogue())


@cache
def _catalogue() -> tuple[tuple[str, Path], ...]:
    files = [path for path in FONTS_DIR.iterdir() if path.suffix.lower() in FONT_SUFFIXES]
    return tuple(sorted((_name(path), path) for path in files))


def _name(path: Path) -> str:
    family, style = ImageFont.truetype(str(path)).getname()
    return " ".join(part for part in (family, style) if part)
