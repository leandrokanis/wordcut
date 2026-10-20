"""Film-style captions timed word by word.

Blocks of up to two lines, yellow with a black outline, shown from their first
word until the next block (or shortly after their last word when a pause
follows). A block closes at a sentence end, at a pause, or when full.
"""

from __future__ import annotations

import platform
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
from PIL import Image, ImageDraw, ImageFont

from cortes_pregacao.transcript import Word

FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)
SENTENCE_END = (".", "?", "!")
MIN_WORDS_BEFORE_SENTENCE_BREAK = 3
PAUSE_BREAK_S = 0.6
LINGER_S = 0.4


@dataclass(frozen=True)
class CaptionStyle:
    size: int = 60
    color: tuple[int, int, int] = (255, 225, 77)  # film-subtitle yellow
    outline: int = 3
    shadow_offset: int = 3
    max_width: int = 960
    max_lines: int = 2
    top: int = 1370  # lower third of 1920; clear of Reels' bottom UI
    line_spacing: float = 1.2


DEFAULT_STYLE = CaptionStyle()


@dataclass(frozen=True)
class Caption:
    start: float
    end: float
    lines: tuple[str, ...]


Measure = Callable[[str], float]


def build_captions(
    words: Sequence[Word], measure: Measure, style: CaptionStyle = DEFAULT_STYLE
) -> list[Caption]:
    blocks = _group(words, measure, style)
    captions: list[Caption] = []
    for index, (block, lines) in enumerate(blocks):
        last_end = block[-1].end
        next_start = blocks[index + 1][0][0].start if index + 1 < len(blocks) else None
        if next_start is not None and next_start - last_end <= LINGER_S:
            end = next_start
        else:
            end = last_end + LINGER_S
        captions.append(Caption(block[0].start, end, tuple(lines)))
    return captions


def _group(
    words: Sequence[Word], measure: Measure, style: CaptionStyle
) -> list[tuple[list[Word], list[str]]]:
    blocks: list[tuple[list[Word], list[str]]] = []
    block: list[Word] = []
    lines: list[str] = []

    def close() -> None:
        nonlocal block, lines
        if block:
            blocks.append((block, lines))
        block, lines = [], []

    for word in words:
        if block and word.start - block[-1].end > PAUSE_BREAK_S:
            close()
        text = _display(word.text)
        if lines and measure(f"{lines[-1]} {text}") <= style.max_width:
            lines[-1] = f"{lines[-1]} {text}"
        elif len(lines) < style.max_lines:
            lines.append(text)
        else:
            close()
            lines.append(text)
        block.append(word)
        if word.text.endswith(SENTENCE_END) and len(block) >= MIN_WORDS_BEFORE_SENTENCE_BREAK:
            close()
    close()
    return blocks


def _display(text: str) -> str:
    return text.replace("...", "…")


def default_font() -> Path:
    for candidate in FONT_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"nenhuma fonte encontrada para legendas ({platform.system()})")


@dataclass(frozen=True)
class CaptionImage:
    """Pre-rendered caption: BGR colour and alpha (0-1), placed at ``top``."""

    caption: Caption
    bgr: npt.NDArray[np.float32]
    alpha: npt.NDArray[np.float32]


class CaptionRenderer:
    def __init__(
        self, frame_width: int, style: CaptionStyle = DEFAULT_STYLE, font: Path | None = None
    ) -> None:
        self.style = style
        self._width = frame_width
        self._font = ImageFont.truetype(str(font or default_font()), style.size)

    def measure(self, text: str) -> float:
        return float(self._font.getlength(text))

    def render(self, caption: Caption) -> CaptionImage:
        style = self.style
        line_height = round(style.size * style.line_spacing)
        height = line_height * len(caption.lines) + 2 * (style.outline + style.shadow_offset)
        image = Image.new("RGBA", (self._width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        for index, line in enumerate(caption.lines):
            x, y = self._width / 2, style.outline + index * line_height
            shadow = (x + style.shadow_offset, y + style.shadow_offset)
            draw.text(shadow, line, font=self._font, anchor="ma", fill=(0, 0, 0, 140))
            draw.text(
                (x, y), line, font=self._font, anchor="ma", fill=(*style.color, 255),
                stroke_width=style.outline, stroke_fill=(0, 0, 0, 255),
            )  # fmt: skip
        rgba = np.asarray(image).astype(np.float32)
        return CaptionImage(caption, rgba[..., 2::-1].copy(), rgba[..., 3:4] / 255.0)
