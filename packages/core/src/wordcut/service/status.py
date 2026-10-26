"""Machine status: whether a heavy operation holds the processing lock (docs/cli.md §10)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from wordcut.db import connect
from wordcut.home import Home
from wordcut.lock import LockHolder, ProcessingLock


def machine_status(home: Home, now: datetime | None = None) -> dict[str, Any]:
    """Who holds the processing lock, never waiting for it; ``now`` defaults to the clock."""
    # docs/cli.md §14: the first call of any command creates and migrates the database.
    connect(home).close()
    holder = ProcessingLock(home).holder()
    if holder is None:
        return {"lock": {"held": False}}
    return {"lock": _held(holder, now or datetime.now().astimezone())}


def _held(holder: LockHolder, now: datetime) -> dict[str, Any]:
    return {
        "held": True,
        **asdict(holder),
        "elapsed_seconds": _elapsed_seconds(holder.started_at, now),
    }


def _elapsed_seconds(started_at: str | None, now: datetime) -> int | None:
    try:
        started = datetime.fromisoformat(started_at or "")
    except ValueError:
        return None
    if started.tzinfo is None:
        return None
    return round((now - started).total_seconds())
