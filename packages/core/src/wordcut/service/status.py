"""Machine status: who holds the processing lock and which tasks run (docs/cli.md §10)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from wordcut.home import Home
from wordcut.lock import LockHolder, ProcessingLock
from wordcut.service.tasks import list_tasks


def machine_status(home: Home, now: datetime | None = None) -> dict[str, Any]:
    """Who holds the processing lock, never waiting for it, and the tasks still running.

    ``now`` defaults to the clock.
    """
    holder = ProcessingLock(home).holder()
    # docs/cli.md §14: listing the tasks creates and migrates the database on the first call.
    running = list_tasks(home, status="running")["items"]
    lock = {"held": False} if holder is None else _held(holder, now or datetime.now().astimezone())
    return {"lock": lock, "running_tasks": running}


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
