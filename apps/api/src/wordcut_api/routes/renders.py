"""Exports of a cut: launch one, estimate it, list and show them and download the file
(docs/api.md)."""

from __future__ import annotations

from contextlib import closing
from typing import Annotated, Any

from fastapi import APIRouter, Body, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, StrictBool

from wordcut import db
from wordcut.service.rendering import estimate_render, show_render, start_render
from wordcut.service.renders import list_renders, render_video
from wordcut.service.tasks import launched_task
from wordcut_api import deps
from wordcut_api.bodies import Changes
from wordcut_api.routes.cuts import without_path

router = APIRouter(prefix="/api")


class RenderChanges(Changes):
    """The options of the export to change, named as the export shows them (docs/cli.md
    §8.7); the others repeat the last ones saved on the cut. A choice is a plain string, so
    the service names its choices."""

    fillers: str | None = None
    stammers: str | None = None
    pauses: str | None = None
    smooth_joins: StrictBool | None = None
    fade: StrictBool | None = None
    normalize: StrictBool | None = None
    caption: StrictBool | None = None
    resolution: str | None = None
    quality: str | None = None


@router.post("/cuts/{cut_id}/renders", status_code=202)
def export(cut_id: int, body: Annotated[RenderChanges | None, Body()] = None) -> dict[str, Any]:
    """Launch the ``render`` task detached (ADR-0007); its progress is in the task's events."""
    changes = {} if body is None else body.given()
    return launched_task(start_render(deps.home(), cut_id, changes, detach=True))


class EstimateQuery(BaseModel):
    """The options of ``RenderChanges`` in the query string, where a switch is written
    ``true`` or ``false``; a parameter it does not declare is refused (ADR-0021)."""

    model_config = ConfigDict(extra="forbid")

    fillers: str | None = None
    stammers: str | None = None
    pauses: str | None = None
    smooth_joins: bool | None = None
    fade: bool | None = None
    normalize: bool | None = None
    caption: bool | None = None
    resolution: str | None = None
    quality: str | None = None


@router.get("/cuts/{cut_id}/renders/estimate")
def estimate(cut_id: int, options: Annotated[EstimateQuery, Query()]) -> dict[str, Any]:
    """How long the export would last and its options, without a task, saving or the lock."""
    with closing(db.connect(deps.home())) as connection:
        return estimate_render(connection, cut_id, options.model_dump(exclude_none=True))


@router.get("/cuts/{cut_id}/renders")
def listing(cut_id: int) -> dict[str, Any]:
    home = deps.home()
    with closing(db.connect(home)) as connection:
        found = list_renders(connection, home, cut_id)
    return {"items": [without_path(export) for export in found["items"]]}


@router.get("/renders/{render_id}")
def show(render_id: int) -> dict[str, Any]:
    home = deps.home()
    with closing(db.connect(home)) as connection:
        return without_path(show_render(connection, home, render_id))


@router.get("/renders/{render_id}/file")
def download(render_id: int) -> FileResponse:
    """The 9:16 video of the export, named as ``render download`` names it."""
    home = deps.home()
    with closing(db.connect(home)) as connection:
        found = render_video(connection, home, render_id)
    return FileResponse(found.path, media_type="video/mp4", filename=found.suggested_name)
