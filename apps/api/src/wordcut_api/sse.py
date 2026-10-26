"""The events of a task as Server-Sent Events (docs/api.md, ADR-0020).

The data of every event is the task as ``service.tasks.show_task`` gives it.
"""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any

from starlette.concurrency import run_in_threadpool

from wordcut.home import Home
from wordcut.service.tasks import WAIT_POLL_SECONDS, show_task

# The stream reads the task as often as ``task wait`` does; it works across processes.
POLL_SECONDS = WAIT_POLL_SECONDS
# A comment this long after the last write keeps proxies from closing an idle stream; nginx
# closes one after 60 s (proxy_read_timeout).
HEARTBEAT_SECONDS = 15.0
HEARTBEAT = ": ping\n\n"

# The event that ends the stream, by final status of the task.
FINAL_EVENTS = {"succeeded": "done", "failed": "failed"}


async def task_events(home: Home, task: dict[str, Any]) -> AsyncIterator[str]:
    """The events of ``task``, as ``show_task`` gave it, until it ends.

    Reading the task never changes it: a client that goes away leaves the task running.
    Asynchronous on purpose: a stream waiting for the next poll holds no thread of the pool
    the synchronous routes run on (ADR-0020).
    """
    heard: tuple[float, str] | None = None
    written_at = time.monotonic()
    while task["status"] not in FINAL_EVENTS:
        progress = (task["progress"], task["progress_message"])
        # As ``wait_task``: only a progress with a message, and only when it changes.
        if task["progress_message"] is not None and progress != heard:
            yield event("progress", task)
            heard, written_at = progress, time.monotonic()
        elif time.monotonic() - written_at >= HEARTBEAT_SECONDS:
            yield HEARTBEAT
            written_at = time.monotonic()
        await asyncio.sleep(POLL_SECONDS)
        task = await run_in_threadpool(show_task, home, task["id"])
    yield event(FINAL_EVENTS[task["status"]], task)


def event(name: str, task: dict[str, Any]) -> str:
    """One SSE event: its name and the task as one line of JSON."""
    return f"event: {name}\ndata: {json.dumps(task)}\n\n"
