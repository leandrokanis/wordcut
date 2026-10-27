"""The media of a sermon's timeline as the clients read it: the thumbnail strip, where each
thumbnail is in the live, and the peaks of the waveform (docs/api.md, ADR-0025)."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, TypeVar

from wordcut import timeline_media
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.sermons import existing_sermon

Media = TypeVar("Media")


def timeline_waveform(connection: sqlite3.Connection, home: Home, sermon_id: int) -> dict[str, Any]:
    """``{"buckets", "peaks"}``: the peaks of the whole live, from 0 to 1, in time order."""
    folder = _folder(connection, home, sermon_id)
    return _found(
        timeline_media.read_waveform(folder),
        f"A forma de onda da pregação {sermon_id} não está disponível.",
        sermon_id,
    )


def timeline_thumbnails_layout(
    connection: sqlite3.Connection, home: Home, sermon_id: int
) -> dict[str, Any]:
    """``{"width", "height", "times"}``: the size of a thumbnail of the strip and the second
    of the live each one shows, in the order they lie side by side."""
    folder = _folder(connection, home, sermon_id)
    return _found(
        timeline_media.read_thumbnails_layout(folder), _no_thumbnails(sermon_id), sermon_id
    )


def timeline_thumbnails(connection: sqlite3.Connection, home: Home, sermon_id: int) -> Path:
    """The JPEG strip of the thumbnails, side by side in time order."""
    folder = _folder(connection, home, sermon_id)
    return _found(timeline_media.thumbnails_image(folder), _no_thumbnails(sermon_id), sermon_id)


def _folder(connection: sqlite3.Connection, home: Home, sermon_id: int) -> Path:
    existing_sermon(connection, sermon_id)
    return home.sermon_timeline(sermon_id)


def _no_thumbnails(sermon_id: int) -> str:
    return f"As miniaturas da pregação {sermon_id} não estão disponíveis."


def _found(media: Media | None, message: str, sermon_id: int) -> Media:
    if media is None:
        # A live without storyboards, a preparation still running or one that failed.
        raise WordcutError("not_found", message, {"sermon_id": sermon_id})
    return media
