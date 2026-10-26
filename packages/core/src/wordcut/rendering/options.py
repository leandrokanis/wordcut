"""The choices of the export dialog, their defaults and how saved and given ones combine
(docs/cli.md §8.7)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from typing import Any

from wordcut.edit.timeline import Cleanup
from wordcut.errors import WordcutError

# docs/cli.md §8.7: the values each choice takes; a switch takes true or false.
CHOICES: dict[str, tuple[Any, ...]] = {
    "fillers": ("remove", "keep"),
    "stammers": ("remove", "keep"),
    "pauses": ("original", "natural", "short"),
    "smooth_joins": (True, False),
    "fade": (True, False),
    "normalize": (True, False),
    "resolution": ("1080x1920", "720x1280"),
    "quality": ("high", "small"),
}


@dataclass(frozen=True)
class RenderOptions:
    """What an export does; the caption comes from the cut's own style instead."""

    fillers: str = "remove"
    stammers: str = "remove"
    pauses: str = "natural"
    smooth_joins: bool = True
    fade: bool = True
    normalize: bool = True
    resolution: str = "1080x1920"
    quality: str = "high"

    @property
    def cleanup(self) -> Cleanup:
        """What the timeline removes with these options."""
        return Cleanup(
            fillers=self.fillers == "remove",
            stammers=self.stammers == "remove",
            pauses=self.pauses,
        )

    def as_dict(self) -> dict[str, Any]:
        """The choices saved on the cut."""
        return asdict(self)

    def summary(self, *, caption: bool) -> dict[str, Any]:
        """The nine choices of the export, in the order of docs/cli.md §8.7, with ``caption``
        on or off as the cut's style is."""
        choices = self.as_dict()
        resolution, quality = choices.pop("resolution"), choices.pop("quality")
        return {**choices, "caption": caption, "resolution": resolution, "quality": quality}


def merged(saved: Mapping[str, Any] | None, changes: Mapping[str, Any]) -> RenderOptions:
    """The options of an export: the ``changes`` given, then those ``saved`` on the cut, then
    the defaults. A saved key that is not an option, or a saved value no longer valid, is left
    out, so options saved by an older version still load."""
    kept = {name: value for name, value in (saved or {}).items() if _is_valid(name, value)}
    return replace(RenderOptions(), **{**kept, **validated(changes)})


def validated(changes: Mapping[str, Any]) -> dict[str, Any]:
    """``changes``, once each is one of its choices; otherwise ``invalid_argument`` naming the
    option and its choices, without the value given (ADR-0015)."""
    for name, value in changes.items():
        if not _is_valid(name, value):
            raise WordcutError(
                "invalid_argument",
                f"Valor inválido para {name}; use um de: {', '.join(map(str, CHOICES[name]))}.",
                {"argument": name, "choices": list(CHOICES[name])},
            )
    return dict(changes)


def _is_valid(name: str, value: Any) -> bool:
    # A bool is checked by type: 1 == True, and 1 is not a switch.
    return name in CHOICES and any(
        type(value) is type(choice) and value == choice for choice in CHOICES[name]
    )
