"""Criteria and presets of the cut suggestion; only an administrator may see or change them
(docs/api.md)."""

from __future__ import annotations

from contextlib import closing
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import StrictBool, StrictInt

from wordcut import db
from wordcut.db.presets import SecondsRange
from wordcut.errors import WordcutError
from wordcut.service.presets import (
    create_preset,
    delete_preset,
    list_criteria,
    list_presets,
    set_default,
    show_preset,
    update_preset,
)
from wordcut_api import deps
from wordcut_api.auth import require
from wordcut_api.bodies import Body, Changes

router = APIRouter(prefix="/api", dependencies=[Depends(require("admin"))])


class NewPreset(Changes):
    """A preset named ``name``, a copy of ``from_id`` or, without it, of the default."""

    name: str
    from_id: StrictInt | None = None


class Seconds(Body):
    """A duration range in whole seconds, as the preset shows it."""

    min: StrictInt
    max: StrictInt


class PresetChanges(Changes):
    """The fields of the preset to change, in the shape the preset shows them (docs/cli.md
    §11.3); ``levels`` changes only the criteria it names."""

    name: str | None = None
    levels: dict[str, str] | None = None
    duration_allowed: Seconds | None = None
    duration_ideal: Seconds | None = None
    reorder: StrictBool | None = None
    protected_words: list[str] | None = None
    instructions: str | None = None

    def given(self) -> dict[str, Any]:
        """The fields given, each duration as the ``SecondsRange`` the service takes."""
        return {
            name: SecondsRange(**value) if name.startswith("duration_") else value
            for name, value in super().given().items()
        }


@router.get("/criteria")
def criteria() -> dict[str, Any]:
    return {"items": list_criteria()}


@router.get("/presets")
def listing() -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return {"items": list_presets(connection)}


@router.get("/presets/{preset_id}")
def show(preset_id: int) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return show_preset(connection, preset_id)


@router.post("/presets", status_code=201)
def create(body: NewPreset) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return create_preset(connection, body.name, from_id=body.from_id)


@router.patch("/presets/{preset_id}")
def change(preset_id: int, body: PresetChanges) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        try:
            return update_preset(connection, preset_id, **body.given())
        except WordcutError as error:
            details = error.details or {}
            if "argument" not in details:
                raise
            named = {**details, "argument": _body_names(details["argument"])}
            raise WordcutError(error.code, error.message, named) from error


@router.post("/presets/{preset_id}/set-default")
def make_default(preset_id: int) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return set_default(connection, preset_id)


@router.delete("/presets/{preset_id}")
def delete(preset_id: int) -> dict[str, Any]:
    """``{"id", "deleted": true}``; the default preset is never deleted."""
    with closing(db.connect(deps.home())) as connection:
        return delete_preset(connection, preset_id)


# The service names the levels after the CLI option ``--level``; the body names them ``levels``.
BODY_NAMES = {"level": "levels"}


def _body_names(argument: str) -> str:
    """The arguments in ``argument``, one or a list of them, named as the fields of the body."""
    return ", ".join(BODY_NAMES.get(name, name) for name in argument.split(", "))
