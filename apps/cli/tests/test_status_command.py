import fcntl
import json
import re
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

import pytest

from wordcut.home import Home
from wordcut.service.tasks import show_task
from wordcut.tasks import Resource
from wordcut.tasks.execution import start
from wordcut_cli import main

StartLockOwner = Callable[[str, str], subprocess.Popen[str]]


def test_status_of_an_idle_machine_is_the_free_lock_in_json(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["status", "--json"])

    assert (exit_code, json.loads(capsys.readouterr().out)) == (
        0,
        {"lock": {"held": False}, "running_tasks": []},
    )


def test_status_without_json_describes_the_holder_in_portuguese(
    lock_owner: StartLockOwner, capsys: pytest.CaptureFixture[str]
) -> None:
    owner = lock_owner("render", "cut 34")

    main(["status"])

    assert re.fullmatch(
        rf"Máquina ocupada: render de cut 34 \(PID {owner.pid}\), desde \S+, há \d+ s\.\n",
        capsys.readouterr().out,
    )


def hold_the_lock_without_description(wordcut_home: Path) -> TextIO:
    wordcut_home.mkdir(parents=True)
    held = (wordcut_home / "processing.lock").open("w")
    fcntl.flock(held, fcntl.LOCK_EX)
    return held


def test_status_while_the_holder_has_not_described_itself_is_busy_with_unknowns(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with hold_the_lock_without_description(wordcut_home):
        exit_code = main(["status"])

    assert (exit_code, capsys.readouterr().out) == (
        0,
        "Máquina ocupada: ? de ? (PID ?), desde ?, há ? s.\n",
    )


def status_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_status_answers_at_once_while_another_process_holds_the_lock(
    lock_owner: StartLockOwner, capsys: pytest.CaptureFixture[str]
) -> None:
    owner = lock_owner("render", "cut 34")

    exit_code, result = status_json(["status", "--json"], capsys)

    lock = result["lock"]
    assert (exit_code, lock["held"], lock["kind"], lock["resource"], lock["pid"]) == (
        0,
        True,
        "render",
        "cut 34",
        owner.pid,
    )


def test_json_option_before_or_after_status_gives_the_same_result(
    lock_owner: StartLockOwner, capsys: pytest.CaptureFixture[str]
) -> None:
    lock_owner("render", "cut 34")
    results = []
    for argv in (["--json", "status"], ["status", "--json"]):
        exit_code, result = status_json(argv, capsys)
        result["lock"].pop("elapsed_seconds")
        results.append((exit_code, result))

    assert results[0] == results[1]


def test_first_status_in_an_empty_data_folder_creates_the_database(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["--json", "status"])

    assert (wordcut_home / "wordcut.db").is_file()


def test_status_shows_the_lock_free_once_its_holder_process_is_killed(
    lock_owner: StartLockOwner, capsys: pytest.CaptureFixture[str]
) -> None:
    owner = lock_owner("render", "cut 34")
    owner.kill()
    owner.wait()

    assert status_json(["status", "--json"], capsys) == (
        0,
        {"lock": {"held": False}, "running_tasks": []},
    )


def test_status_help_shows_an_example_ready_to_copy(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["status", "--help"])

    assert (exit_code, "wordcut status --json" in capsys.readouterr().out) == (0, True)


def running_diagnostic(home: Home) -> int:
    """Launch a detached diagnostic task and return its ID once its process holds the lock."""
    task = start(home, "diagnostic", Resource("sermon", 12), {"seconds": 5}, detach=True)
    while show_task(home, task.id)["progress_message"] is None:
        time.sleep(0.05)
    return task.id


def test_status_names_the_task_holding_the_lock_and_lists_the_running_ones(
    wordcut_home: Path,
    detached_tasks: list[subprocess.Popen[bytes]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    task_id = running_diagnostic(Home(wordcut_home))

    exit_code, result = status_json(["status", "--json"], capsys)

    assert (
        exit_code,
        result["lock"]["task_id"],
        [item["id"] for item in result["running_tasks"]],
    ) == (
        0,
        task_id,
        [task_id],
    )


def test_status_without_json_cites_the_task_and_the_running_tasks(
    wordcut_home: Path,
    detached_tasks: list[subprocess.Popen[bytes]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    task_id = running_diagnostic(Home(wordcut_home))

    main(["status"])

    assert re.fullmatch(
        rf"Máquina ocupada: tarefa {task_id}, diagnostic de sermon 12 \(PID \d+\), desde \S+,"
        rf" há \d+ s\.\nTarefas em andamento:\n  {task_id}  diagnostic  sermon 12  \d+%\n",
        capsys.readouterr().out,
    )
