"""Sermons: create from the live's link, list, show, trim and download (docs/api.md)."""

from __future__ import annotations

from contextlib import closing
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, StrictFloat

from wordcut import db
from wordcut.service.processing import start_processing
from wordcut.service.sermons import (
    create_sermon,
    list_sermons,
    sermon_video,
    show_sermon,
    trim_sermon,
)
from wordcut.service.suggestion import start_suggestion
from wordcut.service.tasks import launched_task
from wordcut_api import deps
from wordcut_api.auth import require

router = APIRouter(prefix="/api/sermons")


# docs/cli.md §7: the choices of ``sermon list --status`` (SERMON_STATES).
SermonState = Literal["created", "trimmed", "processing", "processed", "failed"]


class NewSermon(BaseModel):
    url: str


class Borders(BaseModel):
    """Where the sermon starts and ends, in seconds of the live (docs/cli.md §4.3)."""

    start: StrictFloat
    end: StrictFloat


class ProcessOptions(BaseModel):
    force: bool = False


class SuggestionOptions(BaseModel):
    preset_id: int | None = None


@router.post("", status_code=201)
def create(body: NewSermon) -> JSONResponse:
    """201 with the new sermon; 200 with ``created: false`` when the video already has one."""
    with closing(db.connect(deps.home())) as connection:
        sermon: dict[str, Any] = create_sermon(connection, deps.live_source(), body.url)
    return JSONResponse(sermon, status_code=201 if sermon["created"] else 200)


@router.get("")
def listing(status: SermonState | None = None) -> dict[str, Any]:
    home = deps.home()
    with closing(db.connect(home)) as connection:
        return list_sermons(connection, status, home=home)


@router.get("/{sermon_id}")
def show(sermon_id: int, transcript: bool = False) -> dict[str, Any]:
    home = deps.home()
    with closing(db.connect(home)) as connection:
        return show_sermon(connection, sermon_id, home=home, transcript=transcript)


@router.patch("/{sermon_id}")
def trim(sermon_id: int, body: Borders) -> dict[str, Any]:
    """The trimmed sermon as ``show`` gives it.

    The service's ``needs_reprocess`` stays out, as in the CLI's JSON: the web reads it from
    ``status == "processed"``.
    """
    with closing(db.connect(deps.home())) as connection:
        sermon = trim_sermon(connection, sermon_id, body.start, body.end)
    del sermon["needs_reprocess"]
    return sermon


@router.get("/{sermon_id}/video")
def video(sermon_id: int) -> FileResponse:
    """The processed 16:9 video, named as ``sermon download`` names it."""
    home = deps.home()
    with closing(db.connect(home)) as connection:
        found = sermon_video(connection, home, sermon_id)
    return FileResponse(found.path, media_type="video/mp4", filename=found.suggested_name)


@router.post("/{sermon_id}/process", status_code=202)
def process(
    sermon_id: int, body: Annotated[ProcessOptions | None, Body()] = None
) -> dict[str, Any]:
    """Launch the ``process`` task detached (ADR-0007); its progress is in the task's events."""
    options = body or ProcessOptions()
    task = start_processing(
        deps.home(), sermon_id, live=deps.live_source(), force=options.force, detach=True
    )
    return launched_task(task)


@router.post("/{sermon_id}/suggest", status_code=202, dependencies=[Depends(require("admin"))])
def suggest(
    sermon_id: int, body: Annotated[SuggestionOptions | None, Body()] = None
) -> dict[str, Any]:
    """Launch the ``suggest`` task detached; only an administrator may (feature 1.2.a)."""
    options = body or SuggestionOptions()
    task = start_suggestion(deps.home(), sermon_id, options.preset_id, detach=True)
    return launched_task(task)
