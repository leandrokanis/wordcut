"""The caption style of a cut: what the user chooses, its validation and the drawing style it
becomes (docs/cli.md §8.6; requirement 1.1.f.4)."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, fields, replace
from typing import Any

from wordcut.errors import WordcutError
from wordcut.vertical.captions import DEFAULT_STYLE, CaptionStyle
from wordcut.vertical.fonts import available_fonts

# Inclusive ranges: sizes in px of the 1080x1920 frame, offset in % of the frame height (the
# prototype's "Altura" slider, docs/prototype/wordcut.html).
RANGES: dict[str, tuple[int, int]] = {"size": (24, 160), "offset": (10, 90), "border": (0, 12)}
# The frame the sizes are chosen on (docs/cli.md §8.6).
REFERENCE_FRAME_HEIGHT = 1920
# The height of each position, in % of the frame height, as in the prototype (Topo, Centro,
# Base).
POSITIONS: dict[str, int] = {"top": 20, "center": 50, "bottom": 78}
# Alpha (0-255) and offset in px of the drop shadow; "soft" is the shadow captions always had.
SHADOW_LOOKS: dict[str, tuple[int, int]] = {"none": (0, 0), "soft": (140, 3), "strong": (220, 5)}
SHADOWS = tuple(SHADOW_LOOKS)
COLOURS = ("color", "border_color")
# "#RRGGBB": a hash and six hexadecimal digits, either case.
_HEX_COLOUR = re.compile(r"#[0-9A-Fa-f]{6}")


@dataclass(frozen=True)
class CaptionSettings:
    """The style every caption of a cut is drawn with, as ``cut caption`` shows it."""

    enabled: bool = True
    font: str = "Open Sans Bold"
    size: int = 60
    color: str = "#FFD600"
    position: str = "center"
    offset: int = 50
    border: int = 3
    border_color: str = "#000000"
    shadow: str = "soft"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_CAPTION = CaptionSettings()
_FIELDS = frozenset(field.name for field in fields(CaptionSettings))


def stored_caption(stored: Mapping[str, Any] | None) -> CaptionSettings:
    """The style a cut stored, ``None`` meaning the default; the fields it lacks come from the
    default and keys that are not fields are ignored, so an older style still loads."""
    known = {key: value for key, value in (stored or {}).items() if key in _FIELDS}
    return replace(DEFAULT_CAPTION, **known)


def to_style(settings: CaptionSettings, frame_height: int) -> CaptionStyle:
    """The style ``CaptionRenderer`` draws ``settings`` with, on a 9:16 frame ``frame_height``
    px tall (the frame width is the renderer's). Sizes in px of the 1080x1920 frame scale with
    the frame, so a caption covers the same share of a smaller one."""
    scale = frame_height / REFERENCE_FRAME_HEIGHT
    shadow_alpha, shadow_offset = SHADOW_LOOKS[settings.shadow]
    return CaptionStyle(
        size=round(settings.size * scale),
        color=_rgb(settings.color),
        outline=round(settings.border * scale),
        outline_color=_rgb(settings.border_color),
        shadow_offset=round(shadow_offset * scale),
        shadow_alpha=shadow_alpha,
        max_width=round(DEFAULT_STYLE.max_width * scale),
        centre_y=round(frame_height * settings.offset / 100),
        frame_height=frame_height,
        font=available_fonts()[settings.font],
    )


def _rgb(colour: str) -> tuple[int, int, int]:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def validated(current: CaptionSettings, changes: Mapping[str, Any]) -> CaptionSettings:
    """``current`` with ``changes`` applied, each checked; a refused change raises
    ``invalid_argument`` naming the field in ``details.argument``.

    A ``position`` moves ``offset`` to its height unless ``offset`` comes with it; an
    ``offset`` alone keeps the ``position``.
    """
    checked = {field: _checked(field, value) for field, value in changes.items()}
    if "position" in checked:
        checked.setdefault("offset", POSITIONS[checked["position"]])
    return replace(current, **checked)


def _checked(field: str, value: Any) -> Any:
    if field in RANGES:
        _check_range(field, value)
    elif field in COLOURS:
        return _colour(field, value)
    elif field in _CHOICES:
        _check_choice(field, value, _CHOICES[field]())
    return value


_CHOICES: dict[str, Callable[[], tuple[str, ...]]] = {
    "position": lambda: tuple(POSITIONS),
    "shadow": lambda: SHADOWS,
    "font": lambda: tuple(available_fonts()),
}


def _check_range(field: str, value: int) -> None:
    low, high = RANGES[field]
    if not low <= value <= high:
        raise WordcutError(
            "invalid_argument",
            f"Valor fora da faixa para {field}: use de {low} a {high}.",
            {"argument": field, "min": low, "max": high},
        )


def _check_choice(field: str, value: str, choices: tuple[str, ...]) -> None:
    if value not in choices:
        raise WordcutError(
            "invalid_argument",
            f"Valor inválido para {field}; use um de: {', '.join(choices)}.",
            {"argument": field, "choices": list(choices)},
        )


def _colour(field: str, value: str) -> str:
    if not _HEX_COLOUR.fullmatch(value):
        raise WordcutError(
            "invalid_argument", f"Cor inválida para {field}: use #RRGGBB.", {"argument": field}
        )
    return value.upper()
