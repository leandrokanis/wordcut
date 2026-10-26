"""The criteria of the cut suggestion: filters and values whose prompt text ships with the core.

Each criterion is a file of ``texts/``: a header (``id``, ``name``, ``type``,
``default_level``, ``position``) and one section per level with the prompt piece of that
level. ``texts/base.md`` is the base prompt, a template with the criteria and the durations
as slots; ``texts/options/`` holds the pieces of the edit options and of the additional
instructions. The texts change only by a reviewed commit and never reach a user
(constitution §I); a malformed text is a programming error, raised as ``CatalogError``.
"""

from __future__ import annotations

import functools
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from string import Template

LEVELS = ("lenient", "moderate", "strict")
TYPES = ("filter", "value")
TEXTS = Path(__file__).parent / "texts"

BASE_FILE = "base.md"
OPTIONS_FOLDER = "options"
BASE_SLOTS = ("filters", "values", "allowed_min", "allowed_max", "ideal_min", "ideal_max")
OPTION_SLOTS: Mapping[str, tuple[str, ...]] = {
    "reorder": (),
    "no_reorder": (),
    "protected_words": ("words",),
    "instructions": ("instructions",),
}
HEADER_FIELDS = ("id", "name", "type", "default_level", "position")
SECTION_PREFIX = "## "
CRITERION_ID = re.compile(r"[a-z][a-z_]*")


class CatalogError(Exception):
    """A text of the catalog is malformed: a programming error, caught by the test suite."""


@dataclass(frozen=True)
class Criterion:
    id: str
    name: str
    type: str
    default_level: str
    position: int
    fragments: Mapping[str, str]

    def fragment(self, level: str) -> str:
        """The prompt piece of this criterion at ``level`` (one of ``LEVELS``)."""
        return self.fragments[level]


@dataclass(frozen=True)
class Catalog:
    base: Template
    options: Mapping[str, Template]
    criteria: tuple[Criterion, ...]

    def criterion(self, criterion_id: str) -> Criterion | None:
        return next((found for found in self.criteria if found.id == criterion_id), None)

    def default_levels(self) -> dict[str, str]:
        return {criterion.id: criterion.default_level for criterion in self.criteria}


@functools.cache
def catalog() -> Catalog:
    """The catalog that ships with the package, loaded and validated on first use."""
    return load_catalog(TEXTS)


def load_catalog(directory: Path) -> Catalog:
    """Load and validate the texts of ``directory``, laid out as ``TEXTS`` is."""
    base = _template(directory / BASE_FILE, BASE_SLOTS)
    options = {
        name: _template(directory / OPTIONS_FOLDER / f"{name}.md", slots)
        for name, slots in OPTION_SLOTS.items()
    }
    files = sorted(path for path in directory.glob("*.md") if path.name != BASE_FILE)
    loaded = [(_criterion(path), path) for path in files]
    for attribute in ("id", "position"):
        _check_unique(loaded, attribute)
    criteria = sorted((criterion for criterion, _ in loaded), key=lambda found: found.position)
    return Catalog(base=base, options=options, criteria=tuple(criteria))


def _template(path: Path, slots: tuple[str, ...]) -> Template:
    text = _read(path).strip()
    if not text:
        raise CatalogError(f"{path.name}: empty text")
    missing = [slot for slot in slots if f"${{{slot}}}" not in text]
    if missing:
        raise CatalogError(f"{path.name}: missing slots {', '.join(missing)}")
    template = Template(text)
    try:
        template.substitute(dict.fromkeys(slots, ""))
    except (KeyError, ValueError) as error:
        raise CatalogError(f"{path.name}: unknown or malformed slot ({error})") from error
    return template


def _criterion(path: Path) -> Criterion:
    header_text, _, body = _read(path).partition("\n\n")
    header = _header(path, header_text)
    fragments = _sections(path, body)
    missing = [level for level in LEVELS if not fragments.get(level)]
    if missing:
        raise CatalogError(f"{path.name}: missing or empty levels {', '.join(missing)}")
    if header["type"] not in TYPES:
        raise CatalogError(f"{path.name}: type must be one of {', '.join(TYPES)}")
    if header["default_level"] not in LEVELS:
        raise CatalogError(f"{path.name}: default_level must be one of {', '.join(LEVELS)}")
    if not CRITERION_ID.fullmatch(header["id"]):
        raise CatalogError(f"{path.name}: id must be lowercase snake_case")
    if not header["position"].isdigit():
        raise CatalogError(f"{path.name}: position must be a whole number")
    return Criterion(
        id=header["id"],
        name=header["name"],
        type=header["type"],
        default_level=header["default_level"],
        position=int(header["position"]),
        fragments=fragments,
    )


def _header(path: Path, text: str) -> dict[str, str]:
    header: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition(":")
        if not separator or key.strip() not in HEADER_FIELDS:
            raise CatalogError(f"{path.name}: unexpected header line")
        header[key.strip()] = value.strip()
    missing = [field for field in HEADER_FIELDS if not header.get(field)]
    if missing:
        raise CatalogError(f"{path.name}: missing header fields {', '.join(missing)}")
    return header


def _check_unique(loaded: list[tuple[Criterion, Path]], attribute: str) -> None:
    seen: dict[object, str] = {}
    for criterion, path in loaded:
        value = getattr(criterion, attribute)
        if value in seen:
            raise CatalogError(f"{path.name}: {attribute} repeated from {seen[value]}")
        seen[value] = path.name


def _sections(path: Path, body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in body.splitlines():
        if line.startswith(SECTION_PREFIX):
            level = line.removeprefix(SECTION_PREFIX).strip()
            if level not in LEVELS or level in sections:
                raise CatalogError(f"{path.name}: section that is not a level, or repeated")
            current = sections[level] = []
        elif current is not None:
            current.append(line)
        elif line.strip():
            raise CatalogError(f"{path.name}: text outside a level section")
    return {level: "\n".join(lines).strip() for level, lines in sections.items()}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise CatalogError(f"{path.name}: missing text") from error
