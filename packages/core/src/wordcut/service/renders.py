"""The exports of a cut: list them, show one and give its file to download (docs/cli.md §9)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wordcut.db import renders
from wordcut.db.renders import RenderRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.sermon_folder import folder_name
from wordcut.service.cuts import existing_cut, shown_render
from wordcut.service.sermons import existing_sermon


@dataclass(frozen=True)
class RenderVideo:
    """The 9:16 video of an export and the readable name to save it under."""

    path: Path
    suggested_name: str


def list_renders(connection: sqlite3.Connection, home: Home, cut_id: int) -> dict[str, Any]:
    """The exports of the cut, the most recent first, each as ``render show`` gives it."""
    existing_cut(connection, cut_id)
    return {"items": [shown_render(row, home) for row in renders.newest_of_cut(connection, cut_id)]}


def render_video(connection: sqlite3.Connection, home: Home, render_id: int) -> RenderVideo:
    """The file of the export, named ``AAAA-MM-DD - Título do corte.mp4`` after the service
    date of the cut's sermon."""
    row = existing_render(connection, render_id)
    cut = existing_cut(connection, row.cut_id)
    sermon = existing_sermon(connection, cut.sermon_id)
    return RenderVideo(
        path=_render_file(home, row),
        suggested_name=f"{folder_name(sermon.service_date, cut.title)}.mp4",
    )


def existing_render(connection: sqlite3.Connection, render_id: int) -> RenderRow:
    """The export, or ``not_found`` when there is none with ``render_id``."""
    row = renders.by_id(connection, render_id)
    if row is None:
        raise WordcutError(
            "not_found", f"Exportação {render_id} não existe.", {"render_id": render_id}
        )
    return row


def _render_file(home: Home, row: RenderRow) -> Path:
    file = home.root / row.path
    if not file.is_file():
        # The message stays free of the data folder's path, which is internal (spec 1.1.i.1).
        raise WordcutError(
            "internal_error",
            f"Arquivo da exportação {row.id} não encontrado.",
            {"render_id": row.id},
        )
    return file
