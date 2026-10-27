"""Tasks: list and show them, and follow one by its events (docs/api.md)."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from wordcut.service.tasks import list_tasks, show_task
from wordcut_api import deps, sse

router = APIRouter(prefix="/api/tasks")

# docs/cli.md §6.1: the choices of ``task list`` (TASK_STATES, TASK_KINDS); the internal
# ``diagnostic`` kind is not one of them.
TaskState = Literal["running", "succeeded", "failed"]
TaskKind = Literal["process", "render", "suggest", "prepare"]


@router.get("")
def listing(status: TaskState | None = None, kind: TaskKind | None = None) -> dict[str, Any]:
    return list_tasks(deps.home(), status, kind)


@router.get("/{task_id}")
def show(task_id: int) -> dict[str, Any]:
    return show_task(deps.home(), task_id)


@router.get("/{task_id}/events")
async def events(task_id: int) -> StreamingResponse:
    """The task's events (SSE) until it ends; a missing task is a 404 before any event."""
    home = deps.home()
    task = await run_in_threadpool(show_task, home, task_id)
    return StreamingResponse(sse.task_events(home, task), media_type="text/event-stream")
