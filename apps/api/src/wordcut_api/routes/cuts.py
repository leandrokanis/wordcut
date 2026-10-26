"""Cuts: list, show and preview them, choose, discard or restore them, fix the spelling of
their words and set their caption style (docs/api.md)."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import closing
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import StrictBool, StrictInt

from wordcut import db
from wordcut.errors import WordcutError
from wordcut.service.cuts import (
    caption_of,
    choose_cut,
    discard_cut,
    fix_word,
    list_cuts,
    preview_cut,
    reset_caption,
    restore_cut,
    show_cut,
    update_caption,
)
from wordcut_api import deps
from wordcut_api.bodies import Body, Changes

router = APIRouter(prefix="/api")

# docs/cli.md §8.1: the choices of ``cut list --status`` (CUT_STATES).
CutState = Literal["suggested", "chosen", "discarded"]


class FixedWord(Body):
    """The word with its spelling fixed (docs/cli.md §8.5)."""

    text: str


class CaptionChanges(Changes):
    """The fields of the caption style to change, named as the style shows them
    (docs/cli.md §8.6). A choice is a plain string, so the service names its choices."""

    enabled: StrictBool | None = None
    font: str | None = None
    size: StrictInt | None = None
    color: str | None = None
    position: str | None = None
    offset: StrictInt | None = None
    border: StrictInt | None = None
    border_color: str | None = None
    shadow: str | None = None


@router.get("/sermons/{sermon_id}/cuts")
def listing(sermon_id: int, status: CutState | None = None) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return list_cuts(connection, sermon_id, status)


@router.get("/cuts/{cut_id}")
def show(cut_id: int) -> dict[str, Any]:
    home = deps.home()
    with closing(db.connect(home)) as connection:
        return without_paths(show_cut(connection, cut_id, home=home))


@router.get("/cuts/{cut_id}/preview")
def preview(cut_id: int) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return preview_cut(connection, cut_id)


@router.post("/cuts/{cut_id}/choose")
def choose(cut_id: int) -> dict[str, Any]:
    return _transition(choose_cut, cut_id)


@router.post("/cuts/{cut_id}/discard")
def discard(cut_id: int) -> dict[str, Any]:
    return _transition(discard_cut, cut_id)


@router.post("/cuts/{cut_id}/restore")
def restore(cut_id: int) -> dict[str, Any]:
    return _transition(restore_cut, cut_id)


def _transition(
    change: Callable[[sqlite3.Connection, int], dict[str, Any]], cut_id: int
) -> dict[str, Any]:
    """The cut once ``change`` marks it, as ``GET /api/cuts/{id}`` shows it; its content is
    left as it is (constitution §I)."""
    with closing(db.connect(deps.home())) as connection:
        return without_paths(change(connection, cut_id))


@router.put("/cuts/{cut_id}/words/{word_id}")
def fix(cut_id: int, word_id: int, body: FixedWord) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return fix_word(connection, cut_id, word_id, body.text)


@router.get("/cuts/{cut_id}/caption")
def caption(cut_id: int) -> dict[str, Any]:
    with closing(db.connect(deps.home())) as connection:
        return caption_of(connection, cut_id)


@router.patch("/cuts/{cut_id}/caption")
def change_caption(cut_id: int, body: CaptionChanges) -> dict[str, Any]:
    """The whole style once the fields given change; with none, nothing is stored, unlike
    ``update_caption``, which would mark the cut edited."""
    changes = body.given()
    if not changes:
        raise WordcutError(
            "invalid_argument",
            "Informe ao menos um campo da legenda para alterar.",
            {"argument": ", ".join(CaptionChanges.model_fields)},
        )
    with closing(db.connect(deps.home())) as connection:
        return update_caption(connection, cut_id, changes)


@router.delete("/cuts/{cut_id}/caption")
def reset(cut_id: int) -> dict[str, Any]:
    """The default style, turned on, which the cut follows from now on."""
    with closing(db.connect(deps.home())) as connection:
        return reset_caption(connection, cut_id)


def without_paths(cut: dict[str, Any]) -> dict[str, Any]:
    """The cut with its exports as ``without_path`` gives them."""
    return {**cut, "renders": [without_path(render) for render in cut["renders"]]}


def without_path(export: dict[str, Any]) -> dict[str, Any]:
    """The export without ``path``, its file in the data folder: the web downloads it by
    ``GET /api/renders/{id}/file`` (ADR-0021)."""
    return {key: value for key, value in export.items() if key != "path"}
