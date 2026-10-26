"""Processing a sermon: the ``process`` task (docs/cli.md §7.4)."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime

from wordcut.db import connect, sermons
from wordcut.db.sermons import SermonRow
from wordcut.db.tasks import TaskRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.tasks import ProgressListener, Resource, execution
from wordcut.youtube import LiveSource, YouTubeError


def start_processing(
    home: Home,
    sermon_id: int,
    *,
    live: LiveSource,
    force: bool = False,
    detach: bool,
    on_progress: ProgressListener | None = None,
) -> TaskRow:
    """Start the ``process`` task of the sermon, as ``tasks.execution.start`` does.

    A sermon whose live was still on air when created is looked up on ``live`` once, in
    case it has ended since. The sermon is ``processing`` from the moment the task is
    recorded, under the lock.
    """
    with closing(connect(home)) as connection:
        sermon = _processable(connection, sermon_id, force=force)
        if not sermon.live_finished:
            _require_finished_live(connection, live, sermon)

    def admit() -> None:
        with closing(connect(home)) as connection, connection:
            _processable(connection, sermon_id, force=force)
            sermons.set_status(connection, sermon_id, "processing", _now())

    return execution.start(
        home,
        "process",
        Resource("sermon", sermon_id),
        {"force": force},
        detach=detach,
        on_progress=on_progress,
        admit=admit,
    )


def _processable(connection: sqlite3.Connection, sermon_id: int, *, force: bool) -> SermonRow:
    """The sermon, once it can be processed; otherwise the ``WordcutError`` saying why."""
    sermon = sermons.by_id(connection, sermon_id)
    if sermon is None:
        raise WordcutError(
            "not_found", f"Pregação {sermon_id} não existe.", {"sermon_id": sermon_id}
        )
    if sermon.live_start is None or sermon.live_end is None:
        raise WordcutError(
            "sermon_not_trimmed",
            f"Defina as bordas da pregação {sermon_id} antes de processá-la (sermon trim).",
            {"sermon_id": sermon_id},
        )
    if sermon.status == "processed" and not force:
        raise WordcutError(
            "would_discard_edits",
            f"A pregação {sermon_id} já foi processada; refazer descarta os cortes."
            " Use --force para processar de novo.",
            {"sermon_id": sermon_id},
        )
    return sermon


def _require_finished_live(
    connection: sqlite3.Connection, live: LiveSource, sermon: SermonRow
) -> None:
    """Record the live as finished, from what YouTube says now, or refuse the sermon."""
    try:
        info = live.info(sermon.url)
    except YouTubeError as error:
        raise WordcutError("youtube_error", str(error)) from None
    if not info.is_finished:
        raise WordcutError(
            "live_not_finished",
            f"A live da pregação {sermon.id} ainda não terminou; processe depois que ela acabar.",
            {"sermon_id": sermon.id},
        )
    sermons.update_live(connection, sermon.id, info.duration, True, _now())


def _now() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)
