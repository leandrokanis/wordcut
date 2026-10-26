import _thread
import os
import socket
import subprocess
import threading
import time
from collections.abc import Callable
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, tasks
from wordcut.db.tasks import NewTask, TaskRow
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.lock import ProcessingLock
from wordcut.service.tasks import list_tasks, show_task, wait_task
from wordcut.tasks import Progress, Resource, TaskContext, TaskKind, kind, register
from wordcut.tasks.execution import start

SERMON = Resource("sermon", 12)

StartLockOwner = Callable[[str, str], subprocess.Popen[str]]


def echo_params(ctx: TaskContext) -> dict[str, object]:
    return dict(ctx.params)


ECHO = register(TaskKind(name="test_echo", run=echo_params))


def describe_lock_holder(ctx: TaskContext) -> dict[str, object]:
    holder = ProcessingLock(ctx.home).holder()
    assert holder is not None
    return {"task_id": holder.task_id, "kind": holder.kind, "resource": holder.resource}


register(TaskKind(name="test_lock_probe", run=describe_lock_holder))

REPEATED_REPORTS = 20


def report_repeatedly(ctx: TaskContext) -> dict[str, object]:
    for count in range(REPEATED_REPORTS):
        ctx.progress(count / REPEATED_REPORTS, "contando")
    ctx.progress(1.0, "contado")
    return {}


register(TaskKind(name="test_chatty", run=report_repeatedly))


def start_another_task(ctx: TaskContext) -> dict[str, object]:
    try:
        start(ctx.home, "diagnostic", Resource("cut", 34), {}, detach=False)
    except WordcutError as refused:
        return {"code": refused.code, "details": refused.details}
    return {}


register(TaskKind(name="test_nested", run=start_another_task))

UNLOCKED = register(TaskKind(name="test_unlocked", run=echo_params, needs_lock=False))


def test_a_registered_kind_is_found_by_its_name() -> None:
    assert kind("test_echo") is ECHO


def test_an_unknown_kind_name_is_refused() -> None:
    with pytest.raises(ValueError, match="sermon_on_fire"):
        kind("sermon_on_fire")


def test_task_in_the_foreground_ends_succeeded_with_its_result(wordcut_home: Path) -> None:
    task = start(Home(wordcut_home), "diagnostic", SERMON, {"seconds": 0.2}, detach=False)

    assert (task.status, task.result, task.pid, task.finished_at is not None) == (
        "succeeded",
        {"waited_seconds": 0.2},
        os.getpid(),
        True,
    )


def test_task_holds_the_lock_in_its_own_name_while_it_runs(wordcut_home: Path) -> None:
    task = start(Home(wordcut_home), "test_lock_probe", SERMON, {}, detach=False)

    assert task.result == {"task_id": task.id, "kind": "test_lock_probe", "resource": "sermon 12"}


def test_lock_is_free_once_the_task_ends(wordcut_home: Path) -> None:
    home = Home(wordcut_home)

    start(home, "test_lock_probe", SERMON, {}, detach=False)

    assert ProcessingLock(home).holder() is None


def test_progress_reaches_the_listener_once_it_is_stored_in_the_database(
    wordcut_home: Path,
) -> None:
    home = Home(wordcut_home)
    heard: list[tuple[float, str | None]] = []
    stored: list[tuple[float, str | None]] = []

    def listen(progress: Progress) -> None:
        heard.append((progress.fraction, progress.message))
        with closing(connect(home)) as other:
            task = tasks.by_id(other, progress.task_id)
        assert task is not None
        stored.append((task.progress, task.progress_message))

    start(home, "diagnostic", SERMON, {"seconds": 0.2}, detach=False, on_progress=listen)

    assert (stored, heard[-1]) == (heard, (1.0, "pronto"))


def test_quick_reports_with_the_same_message_are_stored_once(wordcut_home: Path) -> None:
    heard: list[str] = []

    start(
        Home(wordcut_home),
        "test_chatty",
        SERMON,
        {},
        detach=False,
        on_progress=lambda progress: heard.append(progress.message),
    )

    assert heard == ["contando", "contado"]


def stored_task(home: Home, task_id: int) -> TaskRow:
    with closing(connect(home)) as connection:
        task = tasks.by_id(connection, task_id)
    assert task is not None
    return task


def test_task_that_fails_ends_failed_with_its_error_and_raises_it(wordcut_home: Path) -> None:
    home = Home(wordcut_home)
    ids: list[int] = []

    with pytest.raises(WordcutError) as raised:
        start(
            home,
            "diagnostic",
            SERMON,
            {"fail_with": "youtube_error"},
            detach=False,
            on_progress=lambda progress: ids.append(progress.task_id),
        )

    task = stored_task(home, ids[0])
    assert (
        raised.value.code,
        task.status,
        task.error_code,
        task.error_message,
        task.error_details,
        task.finished_at is not None,
    ) == (
        "youtube_error",
        "failed",
        "youtube_error",
        "Falha pedida ao diagnóstico.",
        {"requested": True},
        True,
    )


def test_unexpected_exception_ends_failed_as_internal_error_without_its_text(
    wordcut_home: Path,
) -> None:
    home = Home(wordcut_home)
    ids: list[int] = []

    with pytest.raises(WordcutError) as raised:
        start(
            home,
            "diagnostic",
            SERMON,
            {"crash": True},
            detach=False,
            on_progress=lambda progress: ids.append(progress.task_id),
        )

    task = stored_task(home, ids[0])
    assert (
        raised.value.code,
        task.error_code,
        "crash" in (task.error_message or ""),
        task.error_details,
    ) == ("internal_error", "internal_error", False, None)


def every_task(home: Home) -> list[TaskRow]:
    with closing(connect(home)) as connection:
        return tasks.newest_first(connection)


def test_busy_machine_refuses_a_locking_task_before_recording_it(
    wordcut_home: Path, lock_owner: StartLockOwner
) -> None:
    lock_owner("render", "cut 34")
    home = Home(wordcut_home)

    with pytest.raises(WordcutError) as refused:
        start(home, "diagnostic", SERMON, {}, detach=False)

    assert (refused.value.code, every_task(home)) == ("busy", [])


def test_busy_refusal_names_the_task_holding_the_lock(wordcut_home: Path) -> None:
    task = start(Home(wordcut_home), "test_nested", SERMON, {}, detach=False)

    result: dict[str, Any] = task.result or {}
    assert (result["code"], result["details"]["task_id"]) == ("busy", task.id)


def test_lock_is_free_once_a_task_fails(wordcut_home: Path) -> None:
    home = Home(wordcut_home)

    with pytest.raises(WordcutError):
        start(home, "diagnostic", SERMON, {"fail_with": "youtube_error"}, detach=False)

    assert ProcessingLock(home).holder() is None


def test_task_without_lock_runs_while_another_process_holds_the_lock(
    wordcut_home: Path, lock_owner: StartLockOwner
) -> None:
    lock_owner("render", "cut 34")

    task = start(Home(wordcut_home), "test_unlocked", SERMON, {"tema": "graça"}, detach=False)

    assert (task.status, task.result) == ("succeeded", {"tema": "graça"})


def test_ctrl_c_during_a_foreground_task_ends_it_interrupted_and_frees_the_lock(
    wordcut_home: Path, time_limit: None
) -> None:
    home = Home(wordcut_home)
    ids: list[int] = []
    ctrl_c = threading.Timer(0.3, _thread.interrupt_main)
    ctrl_c.start()

    try:
        with pytest.raises(KeyboardInterrupt):
            start(
                home,
                "diagnostic",
                SERMON,
                {"seconds": 10},
                detach=False,
                on_progress=lambda progress: ids.append(progress.task_id),
            )
    finally:
        ctrl_c.cancel()
        ctrl_c.join()

    task = stored_task(home, ids[0])
    assert (
        task.status,
        task.error_code,
        task.finished_at is not None,
        ProcessingLock(home).holder(),
    ) == ("failed", "interrupted", True, None)


def test_shown_task_has_kind_status_resource_times_progress_error_and_result(
    wordcut_home: Path,
) -> None:
    home = Home(wordcut_home)
    task = start(home, "diagnostic", SERMON, {"seconds": 0.1}, detach=False)

    shown = show_task(home, task.id)

    assert shown == {
        "id": task.id,
        "kind": "diagnostic",
        "status": "succeeded",
        "sermon_id": 12,
        "progress": 1.0,
        "progress_message": "pronto",
        "pid": os.getpid(),
        "started_at": task.started_at.isoformat(),
        "finished_at": task.finished_at.isoformat() if task.finished_at else None,
        "error": None,
        "result": {"waited_seconds": 0.1},
    }


def test_showing_a_task_that_does_not_exist_is_not_found(wordcut_home: Path) -> None:
    with pytest.raises(WordcutError) as missing:
        show_task(Home(wordcut_home), 99)

    assert (missing.value.code, missing.value.exit_code, missing.value.details) == (
        "not_found",
        3,
        {"task_id": 99},
    )


def test_tasks_are_listed_newest_first_only_of_the_status_and_kind_asked_for(
    wordcut_home: Path,
) -> None:
    home = Home(wordcut_home)
    echoed = start(home, "test_echo", SERMON, {}, detach=False)
    diagnosed = start(home, "diagnostic", SERMON, {}, detach=False)
    with pytest.raises(WordcutError):
        start(home, "diagnostic", SERMON, {"fail_with": "youtube_error"}, detach=False)

    listed = [
        [item["id"] for item in list_tasks(home)["items"]][1:],
        [item["id"] for item in list_tasks(home, status="succeeded", kind="diagnostic")["items"]],
    ]

    assert listed == [[diagnosed.id, echoed.id], [diagnosed.id]]


def test_waiting_for_a_succeeded_task_gives_its_result_at_once(wordcut_home: Path) -> None:
    home = Home(wordcut_home)
    task = start(home, "test_echo", SERMON, {"tema": "graça"}, detach=False)

    assert wait_task(home, task.id) == {"tema": "graça"}


def test_waiting_for_a_failed_task_raises_its_error(wordcut_home: Path) -> None:
    home = Home(wordcut_home)
    ids: list[int] = []
    with pytest.raises(WordcutError):
        start(
            home,
            "diagnostic",
            SERMON,
            {"fail_with": "youtube_error"},
            detach=False,
            on_progress=lambda progress: ids.append(progress.task_id),
        )

    with pytest.raises(WordcutError) as failed:
        wait_task(home, ids[0])

    assert (failed.value.code, failed.value.exit_code, failed.value.details) == (
        "youtube_error",
        6,
        {"requested": True},
    )


def ended_process_pid() -> int:
    process = subprocess.Popen(["true"])
    process.wait()
    return process.pid


def recorded_running_task(home: Home, pid: int, host: str | None = None) -> TaskRow:
    new = NewTask(
        kind="diagnostic",
        resource_type="sermon",
        resource_id=12,
        params={},
        pid=pid,
        host=host or socket.gethostname(),
        started_at=datetime.now().astimezone(),
    )
    with closing(connect(home)) as connection:
        return tasks.insert(connection, new)


def test_running_task_whose_process_is_gone_is_shown_failed_as_interrupted(
    wordcut_home: Path,
) -> None:
    home = Home(wordcut_home)
    task = recorded_running_task(home, ended_process_pid())

    shown = show_task(home, task.id)

    assert (shown["status"], shown["error"]["code"], shown["finished_at"] is not None) == (
        "failed",
        "interrupted",
        True,
    )


def test_running_task_whose_process_is_gone_is_listed_failed(wordcut_home: Path) -> None:
    home = Home(wordcut_home)
    recorded_running_task(home, ended_process_pid())

    [listed] = list_tasks(home)["items"]

    assert (listed["status"], listed["error"]["code"]) == ("failed", "interrupted")


def test_waiting_for_a_task_whose_process_is_gone_raises_interrupted(wordcut_home: Path) -> None:
    home = Home(wordcut_home)
    task = recorded_running_task(home, ended_process_pid())

    with pytest.raises(WordcutError) as interrupted:
        wait_task(home, task.id, poll_seconds=0.01)

    assert (interrupted.value.code, interrupted.value.exit_code) == ("interrupted", 1)


def test_running_task_of_a_process_owned_by_another_user_is_still_running(
    wordcut_home: Path,
) -> None:
    home = Home(wordcut_home)
    init_pid = 1
    task = recorded_running_task(home, init_pid)

    assert show_task(home, task.id)["status"] == "running"


def test_running_task_recorded_on_another_host_is_not_judged_by_its_pid(
    wordcut_home: Path,
) -> None:
    home = Home(wordcut_home)
    task = recorded_running_task(home, ended_process_pid(), host="outro-conteiner")

    assert show_task(home, task.id)["status"] == "running"


def test_running_task_holding_the_lock_is_still_running_whatever_its_pid(
    wordcut_home: Path,
) -> None:
    home = Home(wordcut_home)
    task = recorded_running_task(home, ended_process_pid())

    with ProcessingLock(home).acquire("diagnostic", "sermon 12") as held:
        held.assign(task.id)
        status = show_task(home, task.id)["status"]

    assert status == "running"


def test_running_task_whose_process_ended_unreaped_is_shown_failed(
    wordcut_home: Path, time_limit: None
) -> None:
    home = Home(wordcut_home)
    zombie = subprocess.Popen(["true"])
    try:
        while not os.path.exists(f"/proc/{zombie.pid}") or zombie_state(zombie.pid) != "Z":
            time.sleep(0.01)
        task = recorded_running_task(home, zombie.pid)

        status = show_task(home, task.id)["status"]
    finally:
        zombie.wait()

    assert status == "failed"


def zombie_state(pid: int) -> str:
    with open(f"/proc/{pid}/stat") as stat:
        return stat.read().rpartition(")")[2].split()[0]
