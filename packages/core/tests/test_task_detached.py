import os
import signal
import subprocess
import time
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any, NoReturn

import pytest

from wordcut.db import connect, tasks
from wordcut.db.tasks import TaskRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.lock import ProcessingLock
from wordcut.service.tasks import show_task, wait_task
from wordcut.tasks import Resource, execution
from wordcut.tasks.execution import start

SERMON = Resource("sermon", 12)
POLL_SECONDS = 0.05

DetachedTasks = list[subprocess.Popen[bytes]]
StartLockOwner = Callable[[str, str], subprocess.Popen[str]]


def test_detached_task_returns_at_once_while_it_keeps_running(
    wordcut_home: Path, detached_tasks: DetachedTasks
) -> None:
    began = time.monotonic()

    task = start(Home(wordcut_home), "diagnostic", SERMON, {"seconds": 5}, detach=True)

    assert (task.status, time.monotonic() - began < 2) == ("running", True)


def task_once_ended(home: Home, task_id: int) -> TaskRow:
    """The task after its end, polled; the ``time_limit`` fixture bounds the wait."""
    while True:
        with closing(connect(home)) as connection:
            task = tasks.by_id(connection, task_id)
        assert task is not None
        if task.status != "running":
            return task
        time.sleep(POLL_SECONDS)


def test_detached_task_ends_succeeded_by_itself_and_frees_the_lock(
    wordcut_home: Path, detached_tasks: DetachedTasks
) -> None:
    home = Home(wordcut_home)
    launched = start(home, "diagnostic", SERMON, {"seconds": 0.3}, detach=True)

    ended = task_once_ended(home, launched.id)

    assert (ended.status, ended.result, ProcessingLock(home).holder()) == (
        "succeeded",
        {"waited_seconds": 0.3},
        None,
    )


def task_once_reporting(home: Home, task_id: int) -> TaskRow:
    """The task once its process has reported progress, so it holds the lock by then."""
    while True:
        with closing(connect(home)) as connection:
            task = tasks.by_id(connection, task_id)
        assert task is not None
        if task.progress_message is not None:
            return task
        time.sleep(POLL_SECONDS)


def test_detached_task_runs_in_a_session_of_its_own_without_input(
    wordcut_home: Path, detached_tasks: DetachedTasks
) -> None:
    home = Home(wordcut_home)
    task = task_once_reporting(
        home, start(home, "diagnostic", SERMON, {"seconds": 5}, detach=True).id
    )

    assert (os.getsid(task.pid), os.readlink(f"/proc/{task.pid}/fd/0")) == (task.pid, "/dev/null")


def test_detached_task_process_holds_the_lock_in_its_own_name(
    wordcut_home: Path, detached_tasks: DetachedTasks
) -> None:
    home = Home(wordcut_home)
    task = task_once_reporting(
        home, start(home, "diagnostic", SERMON, {"seconds": 5}, detach=True).id
    )

    holder = ProcessingLock(home).holder()

    assert holder is not None
    assert (holder.pid, holder.task_id, holder.kind, task.pid != os.getpid()) == (
        task.pid,
        task.id,
        "diagnostic",
        True,
    )


def test_unexpected_exception_in_a_detached_task_goes_to_its_log_only(
    wordcut_home: Path, detached_tasks: DetachedTasks
) -> None:
    home = Home(wordcut_home)
    launched = start(home, "diagnostic", SERMON, {"crash": True}, detach=True)

    ended = task_once_ended(home, launched.id)

    log = home.task_log(launched.id).read_text()
    assert (ended.error_code, "RuntimeError: diagnostic crash" in log) == ("internal_error", True)


def every_task(home: Home) -> list[TaskRow]:
    with closing(connect(home)) as connection:
        return tasks.newest_first(connection)


def refuse_to_launch(*args: Any, **kwargs: Any) -> NoReturn:
    raise AssertionError("a task process was launched")


def test_busy_machine_launches_no_process_and_records_no_task(
    wordcut_home: Path, lock_owner: StartLockOwner, monkeypatch: pytest.MonkeyPatch
) -> None:
    lock_owner("render", "cut 34")
    monkeypatch.setattr(execution, "Popen", refuse_to_launch)
    home = Home(wordcut_home)

    with pytest.raises(WordcutError) as refused:
        start(home, "diagnostic", SERMON, {}, detach=True)

    logs = list(home.root.glob("tasks/*.log"))
    assert (refused.value.code, every_task(home), logs) == ("busy", [], [])


def test_busy_refusal_names_the_detached_task_holding_the_lock(
    wordcut_home: Path, detached_tasks: DetachedTasks
) -> None:
    home = Home(wordcut_home)
    running = task_once_reporting(
        home, start(home, "diagnostic", SERMON, {"seconds": 5}, detach=True).id
    )

    with pytest.raises(WordcutError) as refused:
        start(home, "diagnostic", Resource("cut", 34), {}, detach=True)

    details = refused.value.details or {}
    assert (refused.value.code, details["task_id"], details["pid"]) == (
        "busy",
        running.id,
        running.pid,
    )


def test_task_whose_process_cannot_start_ends_failed_and_frees_the_lock(
    wordcut_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(execution, "Popen", broken_launch)
    home = Home(wordcut_home)

    with pytest.raises(OSError):
        start(home, "diagnostic", SERMON, {}, detach=True)

    [task] = every_task(home)
    assert (task.status, task.error_code, ProcessingLock(home).holder()) == (
        "failed",
        "internal_error",
        None,
    )


def broken_launch(*args: Any, **kwargs: Any) -> NoReturn:
    raise OSError("no more processes")


def test_launched_task_carries_the_pid_of_its_own_process(
    wordcut_home: Path, detached_tasks: DetachedTasks
) -> None:
    task = start(Home(wordcut_home), "diagnostic", SERMON, {"seconds": 5}, detach=True)

    assert task.pid == detached_tasks[0].pid != os.getpid()


def test_waiting_for_a_detached_task_follows_its_progress_and_frees_the_lock_first(
    wordcut_home: Path, detached_tasks: DetachedTasks
) -> None:
    home = Home(wordcut_home)
    launched = start(home, "diagnostic", SERMON, {"seconds": 1}, detach=True)
    heard: list[str] = []

    result = wait_task(
        home,
        launched.id,
        on_progress=lambda progress: heard.append(progress.message),
        poll_seconds=POLL_SECONDS,
    )

    assert (result, heard[0], ProcessingLock(home).holder()) == (
        {"waited_seconds": 1.0},
        "aguardando",
        None,
    )


def test_killed_task_process_is_shown_failed_as_interrupted_at_the_next_read(
    wordcut_home: Path, detached_tasks: DetachedTasks
) -> None:
    home = Home(wordcut_home)
    task = task_once_reporting(
        home, start(home, "diagnostic", SERMON, {"seconds": 5}, detach=True).id
    )

    os.killpg(task.pid, signal.SIGKILL)
    detached_tasks[0].wait()

    shown = show_task(home, task.id)
    assert (shown["status"], shown["error"]["code"]) == ("failed", "interrupted")
