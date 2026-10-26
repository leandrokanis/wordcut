import fcntl
import json
import socket
import subprocess
import time
from collections.abc import Callable
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from wordcut.db import connect, tasks
from wordcut.db.tasks import NewTask
from wordcut.home import Home
from wordcut.lock import ProcessingLock
from wordcut.service.status import machine_status
from wordcut.service.tasks import show_task
from wordcut.tasks import Resource
from wordcut.tasks.execution import start

StartLockOwner = Callable[[str, str], subprocess.Popen[str]]


def test_machine_with_no_operation_running_reports_the_lock_free(tmp_path: Path) -> None:
    assert machine_status(Home(tmp_path)) == {"lock": {"held": False}, "running_tasks": []}


def test_machine_busy_elsewhere_reports_the_holder_and_how_long_it_has_run(
    wordcut_home: Path, lock_owner: StartLockOwner
) -> None:
    owner = lock_owner("render", "cut 34")
    home = Home(wordcut_home)
    holder = ProcessingLock(home).holder()
    assert holder is not None and holder.started_at is not None
    later = datetime.fromisoformat(holder.started_at) + timedelta(seconds=90)

    assert machine_status(home, now=later) == {
        "lock": {
            "held": True,
            "kind": "render",
            "resource": "cut 34",
            "pid": owner.pid,
            "started_at": holder.started_at,
            "task_id": None,
            "elapsed_seconds": 90,
        },
        "running_tasks": [],
    }


def test_machine_whose_lock_holder_was_killed_reports_the_lock_free(
    wordcut_home: Path, lock_owner: StartLockOwner
) -> None:
    owner = lock_owner("render", "cut 34")
    owner.kill()
    owner.wait()

    assert machine_status(Home(wordcut_home)) == {"lock": {"held": False}, "running_tasks": []}


def test_holder_not_yet_described_is_reported_held_with_unknown_fields(tmp_path: Path) -> None:
    home = Home(tmp_path)
    home.lock_file.touch()

    with home.lock_file.open() as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        status = machine_status(home)

    assert status == {
        "lock": {
            "held": True,
            "kind": None,
            "resource": None,
            "pid": None,
            "started_at": None,
            "task_id": None,
            "elapsed_seconds": None,
        },
        "running_tasks": [],
    }


def test_first_status_call_creates_the_database(tmp_path: Path) -> None:
    home = Home(tmp_path / "vazia")

    machine_status(home)

    assert home.database.is_file()


@pytest.mark.parametrize("started_at", ["ontem", "2026-10-26T19:40:00"])
def test_holder_with_an_unreadable_start_time_has_no_elapsed_time(
    tmp_path: Path, started_at: str
) -> None:
    home = Home(tmp_path)
    home.lock_file.write_text(json.dumps({"kind": "process", "started_at": started_at}))

    with home.lock_file.open() as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        lock = machine_status(home)["lock"]

    assert (lock["started_at"], lock["elapsed_seconds"]) == (started_at, None)


def test_status_lists_the_running_detached_task_and_names_it_as_the_lock_holder(
    wordcut_home: Path, detached_tasks: list[subprocess.Popen[bytes]]
) -> None:
    home = Home(wordcut_home)
    task = start(home, "diagnostic", Resource("sermon", 12), {"seconds": 5}, detach=True)
    while (
        ProcessingLock(home).holder() is None
        or show_task(home, task.id)["progress_message"] is None
    ):
        time.sleep(0.05)

    status = machine_status(home)

    assert (status["lock"]["task_id"], [item["id"] for item in status["running_tasks"]]) == (
        task.id,
        [task.id],
    )


def test_status_shows_no_running_task_whose_process_is_gone(wordcut_home: Path) -> None:
    home = Home(wordcut_home)
    process = subprocess.Popen(["true"])
    process.wait()
    with closing(connect(home)) as connection:
        task = tasks.insert(
            connection,
            NewTask(
                "diagnostic",
                "sermon",
                12,
                {},
                process.pid,
                socket.gethostname(),
                datetime.now().astimezone(),
            ),
        )

    status = machine_status(home)

    assert (status["running_tasks"], show_task(home, task.id)["status"]) == ([], "failed")
