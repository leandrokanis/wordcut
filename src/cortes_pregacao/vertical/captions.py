"""Film-style captions timed word by word.

Blocks of up to two lines in Open Sans Bold, saturated yellow with a black
outline, centred on the frame. Each block shows from its first word until the
next block (or shortly after its last word when a pause follows).

A block never mixes two sentences (or crosses a long pause). A sentence too
long for one block is split into blocks of balanced width, avoiding cuts right
after a weak word ("lembrem-se de / Ester"); inside a block, the two lines are
balanced too.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
from PIL import Image, ImageDraw, ImageFont

from cortes_pregacao.transcript import Word

DEFAULT_FONT = Path(__file__).resolve().parents[1] / "assets/fonts/OpenSans-Bold.ttf"
SENTENCE_END = (".", "?", "!")
PAUSE_BREAK_S = 0.6
CLAUSE_END = (",", ";", ":")
COMMA_PREFERENCE = 0.3  # how much uneven width a break at a comma is worth
WEAK_ENDINGS = frozenset(
    {"a", "o", "as", "os", "à", "ao", "e", "de", "do", "da", "dos", "das", "em", "no", "na",
     "um", "uma", "que", "se", "por", "pra", "para", "com", "seu", "sua", "meu", "minha"}
)  # fmt: skip
LINGER_S = 0.4


@dataclass(frozen=True)
class CaptionStyle:
    size: int = 60
    color: tuple[int, int, int] = (255, 214, 0)  # saturated subtitle yellow
    outline: int = 3
    shadow_offset: int = 3
    max_width: int = 960
    max_lines: int = 2
    centre_y: int = 960  # vertical middle of the 1920 px frame
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


Block = tuple[list[Word], list[str]]


def _group(words: Sequence[Word], measure: Measure, style: CaptionStyle) -> list[Block]:
    blocks: list[Block] = []
    for phrase in _phrases(words):
        blocks.extend(_split_phrase(phrase, measure, style))
    return blocks


def _phrases(words: Sequence[Word]) -> list[list[Word]]:
    """Runs of words ending at a sentence end or before a long pause."""
    phrases: list[list[Word]] = []
    current: list[Word] = []
    for word in words:
        if current and word.start - current[-1].end > PAUSE_BREAK_S:
            phrases.append(current)
            current = []
        current.append(word)
        if word.text.endswith(SENTENCE_END):
            phrases.append(current)
            current = []
    if current:
        phrases.append(current)
    return phrases


def _split_phrase(phrase: list[Word], measure: Measure, style: CaptionStyle) -> list[Block]:
    """Fewest, most even blocks that fit, avoiding weak words before a cut.

    Dynamic programming over cut positions: cost is the squared deviation of
    each block's width from the even share, plus a penalty for a weak ending
    and a bonus for cutting at a comma.
    """
    texts = [_display(word.text) for word in phrase]
    total = measure(" ".join(texts))
    share = total / max(1, -(-int(total) // (style.max_width * style.max_lines)))
    weak_penalty = share**2

    best: list[tuple[float, int]] = [(0.0, 0)] + [(float("inf"), 0)] * len(texts)
    for end in range(1, len(texts) + 1):
        for start in range(end - 1, -1, -1):
            lines = _wrap(texts[start:end], measure, style)
            if lines is None:
                break  # longer blocks starting earlier won't fit either
            cost = best[start][0] + (measure(" ".join(texts[start:end])) - share) ** 2
            if end < len(texts) and _is_weak(texts[end - 1]):
                cost += weak_penalty
            if end < len(texts) and texts[end - 1].endswith(CLAUSE_END):
                cost -= weak_penalty * COMMA_PREFERENCE
            if cost < best[end][0]:
                best[end] = (cost, start)

    blocks: list[Block] = []
    end = len(texts)
    while end > 0:
        start = best[end][1]
        lines = _wrap(texts[start:end], measure, style) or [" ".join(texts[start:end])]
        blocks.append((phrase[start:end], lines))
        end = start
    return blocks[::-1]


def _wrap(texts: list[str], measure: Measure, style: CaptionStyle) -> list[str] | None:
    """One line, or two balanced lines; ``None`` if the words don't fit in two lines.

    A single word wider than the frame still gets its own line.
    """
    whole = " ".join(texts)
    if measure(whole) <= style.max_width or len(texts) == 1:
        return [whole]
    if style.max_lines < 2:
        return None
    options = []
    for cut in range(1, len(texts)):
        top, bottom = " ".join(texts[:cut]), " ".join(texts[cut:])
        widest = max(measure(top), measure(bottom))
        if widest <= style.max_width:
            at_comma = texts[cut - 1].endswith(CLAUSE_END)
            score = widest - (style.max_width * COMMA_PREFERENCE if at_comma else 0)
            options.append((_is_weak(texts[cut - 1]), score, [top, bottom]))
    if not options:
        return None
    return min(options, key=lambda option: (option[0], option[1]))[2]


def _is_weak(text: str) -> bool:
    return text.lower().strip(",;:") in WEAK_ENDINGS


def _display(text: str) -> str:
    return text.replace("...", "…")


@dataclass(frozen=True)
class CaptionImage:
    """Pre-rendered caption: BGR colour and alpha (0-1), placed at row ``top``."""

    caption: Caption
    top: int
    bgr: npt.NDArray[np.float32]
    alpha: npt.NDArray[np.float32]


class CaptionRenderer:
    def __init__(
        self, frame_width: int, style: CaptionStyle = DEFAULT_STYLE, font: Path | None = None
    ) -> None:
        self.style = style
        self._width = frame_width
        self._font = ImageFont.truetype(str(font or DEFAULT_FONT), style.size)

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
        top = style.centre_y - height // 2
        return CaptionImage(caption, top, rgba[..., 2::-1].copy(), rgba[..., 3:4] / 255.0)
