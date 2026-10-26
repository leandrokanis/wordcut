"""Sermons: create one from the live's link, list and show them (docs/cli.md §7.1, §7.2)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from wordcut.db import sermons
from wordcut.db.sermons import NewSermon, SermonRow
from wordcut.errors import WordcutError
from wordcut.youtube import LiveInfo, LiveSource, YouTubeError, video_id

# docs/cli.md §7; the CHECK of migration 0002 lists the same states.
SERMON_STATES = ("created", "trimmed", "processing", "processed", "failed")
# docs/cli.md §8: cut states. Cuts arrive in a later item; until then every count is 0.
CUT_STATES = ("suggested", "chosen", "discarded")


def create_sermon(
    connection: sqlite3.Connection, live: LiveSource, url: str, now: datetime | None = None
) -> dict[str, Any]:
    """Create the sermon of the video ``url`` points to; ``now`` defaults to the clock.

    The same video again returns the existing sermon with ``created: false`` and without
    asking YouTube.
    """
    youtube_id = video_id(url)
    existing = sermons.by_youtube_id(connection, youtube_id)
    if existing is not None:
        return _created(existing, created=False)
    new = _new_sermon(youtube_id, url, _live_info(live, url), now or datetime.now().astimezone())
    try:
        row = sermons.insert(connection, new)
    except sqlite3.IntegrityError:
        # Another create of the same video won the race while this one asked YouTube.
        winner = sermons.by_youtube_id(connection, youtube_id)
        if winner is None:
            raise
        return _created(winner, created=False)
    return _created(row, created=True)


def _created(row: SermonRow, *, created: bool) -> dict[str, Any]:
    return {**_sermon(row), "created": created}


def _live_info(live: LiveSource, url: str) -> LiveInfo:
    try:
        return live.info(url)
    except YouTubeError as error:
        raise WordcutError("youtube_error", str(error)) from None


def _new_sermon(youtube_id: str, url: str, info: LiveInfo, now: datetime) -> NewSermon:
    return NewSermon(
        youtube_id=youtube_id,
        url=url,
        title=info.title,
        service_date=info.service_date,
        live_duration=info.duration,
        live_finished=info.is_finished,
        created_at=now,
    )


def list_sermons(connection: sqlite3.Connection, status: str | None = None) -> dict[str, Any]:
    """Sermons with the latest service first, only those in ``status`` when given."""
    return {"items": [_listed(row) for row in sermons.newest_first(connection, status)]}


def show_sermon(connection: sqlite3.Connection, sermon_id: int) -> dict[str, Any]:
    """The sermon with its borders in the live, its last task and its cuts."""
    row = sermons.by_id(connection, sermon_id)
    if row is None:
        raise WordcutError(
            "not_found", f"Pregação {sermon_id} não existe.", {"sermon_id": sermon_id}
        )
    return {
        **_listed(row),
        "live_start": row.live_start,
        "live_end": row.live_end,
        "last_task": None,
        "cuts": [],
    }


def _listed(row: SermonRow) -> dict[str, Any]:
    return {
        **_sermon(row),
        "duration": None,
        "cut_counts": dict.fromkeys(CUT_STATES, 0),
    }


def _sermon(row: SermonRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "youtube_id": row.youtube_id,
        "url": row.url,
        "title": row.title,
        "service_date": row.service_date.isoformat(),
        "live_duration": row.live_duration,
        "live_finished": row.live_finished,
        "status": row.status,
        "created_at": row.created_at.isoformat(),
    }
