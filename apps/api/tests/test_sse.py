import json
import os
import subprocess
import sys
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from wordcut.db import connect, tasks
from wordcut.db.tasks import NewTask
from wordcut.home import Home
from wordcut.service.tasks import show_task, wait_task
from wordcut.tasks import Resource
from wordcut.tasks.execution import start
from wordcut.tasks.processes import this_host
from wordcut_api import sse

SERMON = Resource("sermon", 12)
STARTED_AT = datetime(2026, 10, 26, 19, 40, tzinfo=timezone(timedelta(hours=-3)))

# One event as the stream delivered it: ("progress" | "done" | "failed", data), or
# (":", text) for a comment.
Event = tuple[str, Any]


@pytest.fixture
def home(wordcut_home: Path) -> Home:
    return Home(wordcut_home)


def recorded_task(home: Home, pid: int) -> int:
    """A ``process`` task recorded ``running`` by the process ``pid``, which runs nothing."""
    new = NewTask(
        kind="process",
        resource_type=SERMON.type,
        resource_id=SERMON.id,
        params={},
        pid=pid,
        host=this_host(),
        started_at=STARTED_AT,
    )
    with closing(connect(home)) as connection:
        return tasks.insert(connection, new).id


def read_events(
    response: Response, enough: Callable[[list[Event]], bool] = lambda events: False
) -> list[Event]:
    """The events of the stream until it closes, or until ``enough`` of them were read."""
    events: list[Event] = []
    name: str | None = None
    data: Any = None
    for line in response.iter_lines():
        if line.startswith(":"):
            events.append((":", line[1:].strip()))
        elif line.startswith("event: "):
            name = line.removeprefix("event: ")
        elif line.startswith("data: "):
            data = json.loads(line.removeprefix("data: "))
        elif line == "" and name is not None:
            events.append((name, data))
            name = None
        if enough(events):
            break
    return events


def test_a_finished_task_streams_done_at_once_and_the_stream_closes(
    assistant: TestClient, home: Home, time_limit: None
) -> None:
    task = start(home, "diagnostic", SERMON, {}, detach=False)

    with assistant.stream("GET", f"/api/tasks/{task.id}/events") as response:
        media_type = response.headers["content-type"].split(";")[0]
        events = read_events(response)

    assert (response.status_code, media_type, events) == (
        200,
        "text/event-stream",
        [("done", show_task(home, task.id))],
    )


@pytest.fixture
def fast_polling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sse, "POLL_SECONDS", 0.05)


def test_a_running_task_streams_its_progress_and_then_done_and_the_stream_closes(
    assistant: TestClient, home: Home, detached_tasks: list[Any], fast_polling: None
) -> None:
    task = start(home, "diagnostic", SERMON, {"seconds": 1}, detach=True)

    with assistant.stream("GET", f"/api/tasks/{task.id}/events") as response:
        events = read_events(response)

    names = [name for name, data in events]
    assert (names[0], names[-1], names.count("done"), events[-1][1]) == (
        "progress",
        "done",
        1,
        show_task(home, task.id),
    )


def test_a_task_that_fails_streams_failed_with_its_error_and_never_done(
    assistant: TestClient, home: Home, detached_tasks: list[Any], fast_polling: None
) -> None:
    task = start(
        home, "diagnostic", SERMON, {"seconds": 0.3, "fail_with": "youtube_error"}, detach=True
    )

    with assistant.stream("GET", f"/api/tasks/{task.id}/events") as response:
        events = read_events(response)

    names = [name for name, data in events]
    assert (names[-1], "done" in names, events[-1][1]["error"]["code"]) == (
        "failed",
        False,
        "youtube_error",
    )


def test_a_task_whose_process_died_streams_failed_as_interrupted(
    assistant: TestClient, home: Home, time_limit: None
) -> None:
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    task_id = recorded_task(home, pid=dead.pid)

    with assistant.stream("GET", f"/api/tasks/{task_id}/events") as response:
        events = read_events(response)

    assert [(name, data["error"]["code"]) for name, data in events] == [("failed", "interrupted")]


def test_the_events_of_a_missing_task_are_a_json_not_found_before_any_stream(
    assistant: TestClient,
) -> None:
    response = assistant.get("/api/tasks/99/events")

    assert (response.status_code, response.headers["content-type"], response.json()) == (
        404,
        "application/json",
        {
            "error": {
                "code": "not_found",
                "message": "Tarefa 99 não existe.",
                "details": {"task_id": 99},
            }
        },
    )


def test_a_client_that_goes_away_leaves_the_task_running_to_its_end(
    assistant: TestClient, home: Home, detached_tasks: list[Any], fast_polling: None
) -> None:
    task = start(home, "diagnostic", SERMON, {"seconds": 2}, detach=True)

    with assistant.stream("GET", f"/api/tasks/{task.id}/events") as response:
        first = read_events(response, enough=lambda events: len(events) == 1)

    assert (first[0][0], wait_task(home, task.id, poll_seconds=0.05)) == (
        "progress",
        {"waited_seconds": 2.0},
    )


def test_an_unchanged_progress_is_sent_once_and_silence_is_filled_with_heartbeats(
    assistant: TestClient, home: Home, time_limit: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sse, "POLL_SECONDS", 0.01)
    monkeypatch.setattr(sse, "HEARTBEAT_SECONDS", 0.05)
    # Recorded by this test's process, alive while it streams: the task stays running.
    task_id = recorded_task(home, pid=os.getpid())
    with closing(connect(home)) as connection:
        tasks.record_progress(connection, task_id, 0.3, "baixando")

    with assistant.stream("GET", f"/api/tasks/{task_id}/events") as response:
        events = read_events(response, enough=lambda events: len(events) == 4)

    assert [data if name == ":" else name for name, data in events] == [
        "progress",
        "ping",
        "ping",
        "ping",
    ]
