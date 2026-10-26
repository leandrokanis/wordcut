import os
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from wordcut.db import connect, tasks
from wordcut.db.tasks import NewTask
from wordcut.home import Home
from wordcut.service.status import machine_status
from wordcut.service.tasks import TASK_KINDS, TASK_STATES, list_tasks, show_task
from wordcut.tasks import Resource
from wordcut.tasks.execution import start
from wordcut.tasks.processes import this_host

SERMON = Resource("sermon", 12)
STARTED_AT = datetime(2026, 10, 26, 19, 40, tzinfo=timezone(timedelta(hours=-3)))


@pytest.fixture
def home(wordcut_home: Path) -> Home:
    return Home(wordcut_home)


def running_task(home: Home, kind: str) -> int:
    """A task recorded ``running`` by this test's process, which stays alive while it runs."""
    new = NewTask(
        kind=kind,
        resource_type=SERMON.type,
        resource_id=SERMON.id,
        params={},
        pid=os.getpid(),
        host=this_host(),
        started_at=STARTED_AT,
    )
    with closing(connect(home)) as connection:
        return tasks.insert(connection, new).id


def test_listing_the_tasks_answers_them_as_task_list_does(
    assistant: TestClient, home: Home
) -> None:
    start(home, "diagnostic", SERMON, {}, detach=False)
    running_task(home, "process")

    response = assistant.get("/api/tasks")

    assert (response.status_code, response.json(), len(response.json()["items"])) == (
        200,
        list_tasks(home),
        2,
    )


def test_listing_by_status_and_kind_answers_only_those_tasks(
    assistant: TestClient, home: Home
) -> None:
    running_task(home, "process")
    wanted = running_task(home, "suggest")
    finished = running_task(home, "suggest")
    with closing(connect(home)) as connection:
        tasks.finish_succeeded(connection, finished, {}, STARTED_AT)

    response = assistant.get("/api/tasks", params={"status": "running", "kind": "suggest"})

    assert (
        [item["id"] for item in response.json()["items"]],
        response.json(),
    ) == ([wanted], list_tasks(home, "running", "suggest"))


@pytest.mark.parametrize(
    ("argument", "typed", "choices"),
    [
        ("kind", "diagnostic", TASK_KINDS),
        ("kind", "segredo-digitado", TASK_KINDS),
        ("status", "segredo-digitado", TASK_STATES),
    ],
    ids=["internal diagnostic kind", "unknown kind", "unknown status"],
)
def test_a_filter_outside_the_choices_is_invalid_argument_with_the_choices(
    argument: str, typed: str, choices: tuple[str, ...], assistant: TestClient
) -> None:
    response = assistant.get("/api/tasks", params={argument: typed})

    error = response.json()["error"]
    assert (response.status_code, error["code"], error["details"], typed in response.text) == (
        400,
        "invalid_argument",
        {"argument": argument, "choices": list(choices)},
        False,
    )


def test_showing_a_task_answers_it_as_task_show_does(assistant: TestClient, home: Home) -> None:
    task = start(home, "diagnostic", SERMON, {"seconds": 0}, detach=False)

    response = assistant.get(f"/api/tasks/{task.id}")

    assert (response.status_code, response.json()) == (200, show_task(home, task.id))


def test_showing_a_missing_task_is_not_found_with_its_id(assistant: TestClient) -> None:
    response = assistant.get("/api/tasks/99")

    assert (response.status_code, response.json()["error"]["details"]) == (404, {"task_id": 99})


def test_the_status_of_a_free_machine_is_the_one_status_gives(
    assistant: TestClient, home: Home
) -> None:
    response = assistant.get("/api/status")

    assert (response.status_code, response.json()) == (200, machine_status(home))


def without_elapsed_seconds(status: dict[str, Any]) -> dict[str, Any]:
    """The status without the lock's ``elapsed_seconds``, which follows the clock."""
    lock = {field: value for field, value in status["lock"].items() if field != "elapsed_seconds"}
    return {**status, "lock": lock}


def test_the_status_of_a_busy_machine_is_the_one_status_gives(
    assistant: TestClient, home: Home, lock_owner: Any
) -> None:
    lock_owner("process", "sermon 12")
    running_task(home, "process")

    response = assistant.get("/api/status")

    shown = response.json()
    assert (
        without_elapsed_seconds(shown),
        shown["lock"]["held"],
        len(shown["running_tasks"]),
    ) == (without_elapsed_seconds(machine_status(home)), True, 1)
