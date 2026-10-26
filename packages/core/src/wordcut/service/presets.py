"""Presets of the cut suggestion: levels of the criteria, durations, edit options and
additional instructions (docs/cli.md §11.3), and the prompt of a preset (FR-007).

A preset never carries prompt text: only the level of each criterion, by ID. Reading a
preset completes the criteria it lacks with their default level and drops the IDs the
catalog no longer has (FR-006).
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import datetime
from typing import Any

from wordcut.criteria import LEVELS, catalog
from wordcut.db import presets
from wordcut.db.presets import PresetFields, PresetRow, SecondsRange
from wordcut.errors import WordcutError

# Keeps the additional instructions from outgrowing the criteria in the prompt.
INSTRUCTIONS_LIMIT = 4000
# "<min>-<max>" in whole seconds, as docs/cli.md §11.3 writes a duration.
SECONDS_RANGE = re.compile(r"\s*(\d+)\s*-\s*(\d+)\s*")
UPDATE_ARGUMENTS = (
    "name, level, duration_allowed, duration_ideal, reorder, protected_words, instructions"
)


def list_criteria() -> list[dict[str, str]]:
    """The criteria of the code, without their prompt text (constitution §I, FR-002)."""
    return [
        {
            "id": criterion.id,
            "name": criterion.name,
            "type": criterion.type,
            "default_level": criterion.default_level,
        }
        for criterion in catalog().criteria
    ]


def list_presets(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [_shown(row) for row in presets.all_presets(connection)]


def show_preset(connection: sqlite3.Connection, preset_id: int) -> dict[str, Any]:
    return _shown(_existing(connection, preset_id))


def default_preset(connection: sqlite3.Connection) -> dict[str, Any]:
    """The preset the automatic suggestion uses."""
    return _shown(_default(connection))


def create_preset(
    connection: sqlite3.Connection,
    name: str,
    from_id: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create a preset named ``name`` as a copy of ``from_id``, or of the default when
    ``from_id`` is not given; the copy is not the default. ``now`` defaults to the clock."""
    source = _default(connection) if from_id is None else _existing(connection, from_id)
    fields = _fields_of(source, name=_valid_name(connection, name))
    with connection:
        row = presets.insert(connection, fields, _now(now))
    return _shown(row)


def update_preset(
    connection: sqlite3.Connection,
    preset_id: int,
    *,
    name: str | None = None,
    levels: Mapping[str, str] | None = None,
    duration_allowed: SecondsRange | None = None,
    duration_ideal: SecondsRange | None = None,
    reorder: bool | None = None,
    protected_words: Sequence[str] | None = None,
    instructions: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Change the fields given, leave the others as they are, and show the preset.

    ``levels`` maps criterion IDs to levels and changes only those criteria.
    """
    row = _existing(connection, preset_id)
    changes: dict[str, Any] = {}
    if name is not None:
        changes["name"] = _valid_name(connection, name, preset_id)
    if levels is not None:
        changes["levels"] = {**row.levels, **_valid_levels(levels)}
    if duration_allowed is not None:
        changes["duration_allowed"] = _valid_range(duration_allowed, "duration_allowed")
    if duration_ideal is not None:
        changes["duration_ideal"] = _valid_range(duration_ideal, "duration_ideal")
    if reorder is not None:
        changes["reorder"] = reorder
    if protected_words is not None:
        changes["protected_words"] = _normalized_words(protected_words)
    if instructions is not None:
        changes["instructions"] = _valid_instructions(instructions)
    if not changes:
        raise WordcutError(
            "invalid_argument",
            "Informe ao menos um campo do preset para alterar.",
            {"argument": UPDATE_ARGUMENTS},
        )
    fields = _fields_of(row, **changes)
    _check_ideal_fits(fields, "duration_allowed" if duration_ideal is None else "duration_ideal")
    with connection:
        presets.update(connection, preset_id, fields, _now(now))
    return show_preset(connection, preset_id)


def set_default(
    connection: sqlite3.Connection, preset_id: int, now: datetime | None = None
) -> dict[str, Any]:
    """Make the preset the default, in place of the current one, and show it."""
    row = _existing(connection, preset_id)
    previous = _default(connection)
    if previous.id != row.id:
        moment = _now(now)
        with connection:
            presets.set_default_flag(connection, previous.id, False, moment)
            presets.set_default_flag(connection, row.id, True, moment)
    return show_preset(connection, preset_id)


def delete_preset(connection: sqlite3.Connection, preset_id: int) -> dict[str, Any]:
    """Delete a preset other than the default (FR-005)."""
    row = _existing(connection, preset_id)
    if row.is_default:
        raise WordcutError(
            "default_preset",
            "O preset padrão não pode ser apagado; torne outro preset o padrão antes.",
            {"preset_id": preset_id},
        )
    with connection:
        presets.delete(connection, preset_id)
    return {"id": preset_id, "deleted": True}


def build_prompt(preset: Mapping[str, Any]) -> str:
    """The prompt of the cut suggestion for ``preset``, as ``show_preset`` gives it (FR-007).

    The base prompt with the piece of each criterion at the preset's level (a criterion the
    preset lacks at its default level) and the preset's durations, then the edit options and,
    last, the administrator's additional instructions. Pure: no network, no LLM.
    """
    known = catalog()
    levels: Mapping[str, str] = preset["levels"]

    def pieces(kind: str) -> str:
        return "\n".join(
            criterion.fragment(levels.get(criterion.id, criterion.default_level))
            for criterion in known.criteria
            if criterion.type == kind
        )

    allowed, ideal = preset["duration_allowed"], preset["duration_ideal"]
    sections = [
        known.base.substitute(
            filters=pieces("filter"),
            values=pieces("value"),
            allowed_min=allowed["min"],
            allowed_max=allowed["max"],
            ideal_min=ideal["min"],
            ideal_max=ideal["max"],
        ),
        known.options["reorder" if preset["reorder"] else "no_reorder"].substitute(),
    ]
    words: Sequence[str] = preset["protected_words"]
    if words:
        quoted = ", ".join(f'"{word}"' for word in words)
        sections.append(known.options["protected_words"].substitute(words=quoted))
    instructions = preset["instructions"].strip()
    if instructions:
        sections.append(known.options["instructions"].substitute(instructions=instructions))
    return "\n\n".join(sections)


def parse_seconds_range(text: str, argument: str) -> SecondsRange:
    """Read a duration written ``<min>-<max>`` in whole seconds (``55-65``)."""
    match = SECONDS_RANGE.fullmatch(text)
    if match is None:
        raise WordcutError(
            "invalid_argument",
            "Escreva a duração como <mínimo>-<máximo> em segundos inteiros, como 55-65.",
            {"argument": argument},
        )
    return SecondsRange(int(match[1]), int(match[2]))


def parse_level(text: str) -> tuple[str, str]:
    """Read a level written ``<criterion>=<level>`` (``allegory=strict``)."""
    criterion_id, separator, level = text.partition("=")
    if not separator:
        raise WordcutError(
            "invalid_argument",
            "Escreva o nível como <critério>=<nível>, como allegory=strict.",
            {"argument": "level"},
        )
    return criterion_id.strip(), level.strip()


def parse_protected_words(text: str) -> list[str]:
    """Read protected words separated by commas (``"não,mas,se"``)."""
    return text.split(",")


def _valid_name(connection: sqlite3.Connection, name: str, preset_id: int | None = None) -> str:
    stripped = name.strip()
    if not stripped:
        raise WordcutError(
            "invalid_argument", "O nome do preset não pode ficar vazio.", {"argument": "name"}
        )
    same_name = presets.by_name(connection, stripped)
    if same_name is not None and same_name.id != preset_id:
        raise WordcutError(
            "invalid_argument", "Já existe um preset com esse nome.", {"argument": "name"}
        )
    return stripped


def _valid_levels(levels: Mapping[str, str]) -> dict[str, str]:
    known = catalog()
    for criterion_id, level in levels.items():
        if known.criterion(criterion_id) is None:
            raise WordcutError(
                "invalid_argument",
                "Critério inexistente; os critérios estão em wordcut criteria list.",
                {"argument": "level"},
            )
        if level not in LEVELS:
            raise WordcutError(
                "invalid_argument",
                f"Nível inválido; use um de: {', '.join(LEVELS)}.",
                {"argument": "level", "choices": list(LEVELS)},
            )
    return dict(levels)


def _valid_range(seconds: SecondsRange, argument: str) -> SecondsRange:
    if seconds.min > seconds.max:
        raise WordcutError(
            "invalid_argument",
            "O mínimo da duração não pode passar do máximo.",
            {"argument": argument},
        )
    return seconds


def _check_ideal_fits(fields: PresetFields, argument: str) -> None:
    allowed, ideal = fields.duration_allowed, fields.duration_ideal
    if ideal.min < allowed.min or ideal.max > allowed.max:
        raise WordcutError(
            "invalid_argument",
            "A duração ideal precisa caber na duração permitida.",
            {"argument": argument},
        )


def _normalized_words(words: Sequence[str]) -> tuple[str, ...]:
    stripped = (word.strip() for word in words)
    return tuple(dict.fromkeys(word for word in stripped if word))


def _valid_instructions(text: str) -> str:
    instructions = text.strip()
    if len(instructions) > INSTRUCTIONS_LIMIT:
        raise WordcutError(
            "invalid_argument",
            f"As instruções passam de {INSTRUCTIONS_LIMIT} caracteres.",
            {"argument": "instructions"},
        )
    return instructions


def _default(connection: sqlite3.Connection) -> PresetRow:
    row = presets.default(connection)
    # FR-005: migration 0006 seeds the default and the service never leaves it without one.
    assert row is not None
    return row


def _fields_of(row: PresetRow, **changes: Any) -> PresetFields:
    fields = PresetFields(
        name=row.name,
        levels=row.levels,
        duration_allowed=row.duration_allowed,
        duration_ideal=row.duration_ideal,
        reorder=row.reorder,
        protected_words=row.protected_words,
        instructions=row.instructions,
    )
    return replace(fields, **changes)


def _now(now: datetime | None) -> datetime:
    return now or datetime.now().astimezone()


def _existing(connection: sqlite3.Connection, preset_id: int) -> PresetRow:
    row = presets.by_id(connection, preset_id)
    if row is None:
        raise WordcutError("not_found", f"Preset {preset_id} não existe.", {"preset_id": preset_id})
    return row


def _shown(row: PresetRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "is_default": row.is_default,
        "levels": _levels(row.levels),
        "duration_allowed": _range(row.duration_allowed),
        "duration_ideal": _range(row.duration_ideal),
        "reorder": row.reorder,
        "protected_words": list(row.protected_words),
        "instructions": row.instructions,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


def _levels(stored: dict[str, str]) -> dict[str, str]:
    return {
        criterion.id: stored.get(criterion.id, criterion.default_level)
        for criterion in catalog().criteria
    }


def _range(seconds: SecondsRange) -> dict[str, int]:
    return {"min": seconds.min, "max": seconds.max}
