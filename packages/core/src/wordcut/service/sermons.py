"""Sermons: create one from the live's link, list, show and trim them (docs/cli.md §7.1-§7.3)."""

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
# 1.1.b: a sermon lasts at least one minute.
MIN_SERMON_SECONDS = 60
# Borders are kept to the millisecond, the precision of HH:MM:SS.mmm (docs/cli.md §2).
MILLISECOND_DIGITS = 3

# Start and end of the sermon, in seconds of the live.
Borders = tuple[float, float]


def create_sermon(
    connection: sqlite3.Connection,
    live: LiveSource,
    url: str,
    now: datetime | None = None,
    *,
    start: float | None = None,
    end: float | None = None,
) -> dict[str, Any]:
    """Create the sermon of the video ``url`` points to; ``now`` defaults to the clock.

    The same video again returns the existing sermon with ``created: false`` and without
    asking YouTube. With ``start`` and ``end`` (both or neither), the new or existing
    sermon is trimmed as ``trim_sermon`` does, and the answer carries its
    ``needs_reprocess``.
    """
    borders = _requested_borders(start, end)
    moment = now or datetime.now().astimezone()
    youtube_id = video_id(url)
    existing = sermons.by_youtube_id(connection, youtube_id)
    if existing is None:
        row, created = _inserted(connection, live, youtube_id, url, moment, borders)
    else:
        row, created = existing, False
    if borders is None:
        return _created(row, created=created)
    trimmed = _record_range(connection, row, *borders, moment)
    return {**_created(trimmed, created=created), "needs_reprocess": _needs_reprocess(row)}


def _requested_borders(start: float | None, end: float | None) -> Borders | None:
    if start is None and end is None:
        return None
    if start is None or end is None:
        raise WordcutError(
            "invalid_argument",
            "Informe o início e o fim da pregação, ou nenhum dos dois.",
            {"argument": "start" if start is None else "end"},
        )
    return start, end


def _inserted(
    connection: sqlite3.Connection,
    live: LiveSource,
    youtube_id: str,
    url: str,
    now: datetime,
    borders: Borders | None,
) -> tuple[SermonRow, bool]:
    """The new sermon and true, or the one a concurrent create inserted first and false."""
    info = _live_info(live, url)
    if borders is not None:
        # Checked before the insert, so refused borders leave no sermon behind.
        _checked_range(*borders, info.duration)
    try:
        return sermons.insert(connection, _new_sermon(youtube_id, url, info, now)), True
    except sqlite3.IntegrityError:
        # Another create of the same video won the race while this one asked YouTube.
        winner = sermons.by_youtube_id(connection, youtube_id)
        if winner is None:
            raise
        return winner, False


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
    return _shown(_existing(connection, sermon_id))


def _existing(connection: sqlite3.Connection, sermon_id: int) -> SermonRow:
    row = sermons.by_id(connection, sermon_id)
    if row is None:
        raise WordcutError(
            "not_found", f"Pregação {sermon_id} não existe.", {"sermon_id": sermon_id}
        )
    return row


def trim_sermon(
    connection: sqlite3.Connection,
    sermon_id: int,
    start: float,
    end: float,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Record where the sermon starts and ends in the live, in seconds of the live.

    Returns the sermon as ``show_sermon`` does, plus ``needs_reprocess``: true when the
    sermon was already processed, which keeps its status and its cuts until reprocessed.
    """
    row = _existing(connection, sermon_id)
    trimmed = _record_range(connection, row, start, end, now or datetime.now().astimezone())
    return {**_shown(trimmed), "needs_reprocess": _needs_reprocess(row)}


def _record_range(
    connection: sqlite3.Connection, row: SermonRow, start: float, end: float, now: datetime
) -> SermonRow:
    if row.status == "processing":
        raise WordcutError("busy", f"A pregação {row.id} está sendo processada.")
    start, end = _checked_range(start, end, row.live_duration)
    status = row.status if _needs_reprocess(row) else "trimmed"
    sermons.update_range(connection, row.id, start, end, status, now)
    return _existing(connection, row.id)


def _needs_reprocess(row: SermonRow) -> bool:
    return row.status == "processed"


def _checked_range(start: float, end: float, live_duration: float | None) -> Borders:
    """The borders kept to the millisecond, once they make a sermon inside the live."""
    start, end = _to_millisecond(start), _to_millisecond(end)
    if not _within_live(start, end, live_duration):
        raise WordcutError(
            "invalid_argument",
            "As bordas precisam estar dentro da live, com o início antes do fim.",
            {"start": start, "end": end, "live_duration": live_duration},
        )
    duration = _duration(start, end)
    if duration < MIN_SERMON_SECONDS:
        raise WordcutError(
            "sermon_too_short",
            f"A pregação precisa ter pelo menos {MIN_SERMON_SECONDS} s; a faixa tem {duration} s.",
            {"duration": duration, "min_duration": MIN_SERMON_SECONDS},
        )
    return start, end


def _within_live(start: float, end: float, live_duration: float | None) -> bool:
    return 0 <= start < end and (live_duration is None or end <= live_duration)


def _duration(start: float, end: float) -> float:
    return _to_millisecond(end - start)


def _to_millisecond(seconds: float) -> float:
    return round(seconds, MILLISECOND_DIGITS)


def _shown(row: SermonRow) -> dict[str, Any]:
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
        "duration": _sermon_duration(row),
        "cut_counts": dict.fromkeys(CUT_STATES, 0),
    }


def _sermon_duration(row: SermonRow) -> float | None:
    if row.live_start is None or row.live_end is None:
        return None
    return _duration(row.live_start, row.live_end)


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
