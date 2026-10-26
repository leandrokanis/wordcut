import _thread
import json
import os
import re
import subprocess
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Any

import pytest

from wordcut.home import Home
from wordcut.lock import ProcessingLock
from wordcut.service.tasks import list_tasks, show_task, wait_task
from wordcut.tasks import Resource
from wordcut.tasks.execution import start
from wordcut_cli import main
from wordcut_cli.contract import Parser, add_command, create_parser, execute
from wordcut_cli.tasks_support import add_wait_option, launch

SERMON = Resource("sermon", 12)


@contextmanager
def ctrl_c_after(seconds: float) -> Iterator[None]:
    """Press Ctrl+C ``seconds`` into the block, as the terminal would (SIGINT to the CLI)."""
    timer = threading.Timer(seconds, _thread.interrupt_main)
    timer.start()
    try:
        yield
    finally:
        timer.cancel()
        timer.join()


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_task_show_prints_the_task_in_json(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = Home(wordcut_home)
    task = start(home, "diagnostic", SERMON, {}, detach=False)

    assert run_json(["task", "show", str(task.id), "--json"], capsys) == (
        0,
        show_task(home, task.id),
    )


def test_task_show_of_a_missing_task_is_not_found_with_exit_3(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(["task", "show", "99", "--json"], capsys)

    assert (exit_code, answer["error"]["code"], answer["error"]["details"]) == (
        3,
        "not_found",
        {"task_id": 99},
    )


def test_task_show_without_json_describes_the_task_in_portuguese(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    task = start(Home(wordcut_home), "diagnostic", SERMON, {}, detach=False)

    main(["task", "show", str(task.id)])

    out = capsys.readouterr().out
    assert out.startswith(f"Tarefa {task.id}: diagnostic de sermon 12\nEstado: concluída\n")


def test_task_list_prints_the_tasks_of_the_status_and_kind_asked_for(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = Home(wordcut_home)
    done = start(home, "diagnostic", SERMON, {}, detach=False)

    exit_code, listed = run_json(["task", "list", "--status", "succeeded", "--json"], capsys)

    assert (exit_code, [item["id"] for item in listed["items"]]) == (0, [done.id])


@pytest.mark.parametrize("option", [["--status", "parada"], ["--kind", "diagnostic"]])
def test_task_list_refuses_a_status_or_kind_outside_the_choices(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str], option: list[str]
) -> None:
    exit_code, answer = run_json(["task", "list", *option, "--json"], capsys)

    assert (exit_code, answer["error"]["code"]) == (2, "invalid_argument")


def test_json_option_before_or_after_task_gives_the_same_result(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    start(Home(wordcut_home), "diagnostic", SERMON, {}, detach=False)

    results = [
        run_json(argv, capsys) for argv in (["--json", "task", "list"], ["task", "list", "--json"])
    ]

    assert results[0] == results[1]


def test_task_list_without_json_has_one_line_per_task(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    task = start(Home(wordcut_home), "diagnostic", SERMON, {}, detach=False)

    main(["task", "list"])

    assert capsys.readouterr().out == f"{task.id}  concluída  diagnostic  sermon 12  100%\n"


def test_diagnostic_task_is_not_offered_by_the_cli(capsys: pytest.CaptureFixture[str]) -> None:
    for argv in (["--help"], ["task", "--help"], ["task", "list", "--help"]):
        main(argv)

    assert "diagnostic" not in capsys.readouterr().out


DetachedTasks = list[subprocess.Popen[bytes]]
StartLockOwner = Callable[[str, str], subprocess.Popen[str]]


def test_task_wait_shows_progress_on_stderr_and_the_result_on_stdout(
    wordcut_home: Path, detached_tasks: DetachedTasks, capsys: pytest.CaptureFixture[str]
) -> None:
    task = start(Home(wordcut_home), "diagnostic", SERMON, {"seconds": 1}, detach=True)

    exit_code = main(["task", "wait", str(task.id), "--json"])

    out, err = capsys.readouterr()
    progress_line = re.match(r"\[diagnostic\] aguardando \d+%\n", err)
    assert (exit_code, json.loads(out), progress_line is not None) == (
        0,
        {"waited_seconds": 1.0},
        True,
    )


def test_task_wait_of_a_failed_task_prints_its_error_and_exits_with_its_code(
    wordcut_home: Path, detached_tasks: DetachedTasks, capsys: pytest.CaptureFixture[str]
) -> None:
    params = {"seconds": 0.2, "fail_with": "youtube_error"}
    task = start(Home(wordcut_home), "diagnostic", SERMON, params, detach=True)

    exit_code, answer = run_json(["task", "wait", str(task.id), "--json"], capsys)

    assert (exit_code, answer["error"]) == (
        6,
        {
            "code": "youtube_error",
            "message": "Falha pedida ao diagnóstico.",
            "details": {"requested": True},
        },
    )


def test_ctrl_c_in_task_wait_stops_waiting_and_leaves_the_task_running(
    wordcut_home: Path, detached_tasks: DetachedTasks, capsys: pytest.CaptureFixture[str]
) -> None:
    home = Home(wordcut_home)
    task = start(home, "diagnostic", SERMON, {"seconds": 3}, detach=True)

    with ctrl_c_after(0.3):
        exit_code = main(["task", "wait", str(task.id), "--json"])

    assert (exit_code, wait_task(home, task.id, poll_seconds=0.05)) == (
        130,
        {"waited_seconds": 3.0},
    )


def test_quiet_task_wait_prints_no_progress(
    wordcut_home: Path, detached_tasks: DetachedTasks, capsys: pytest.CaptureFixture[str]
) -> None:
    task = start(Home(wordcut_home), "diagnostic", SERMON, {"seconds": 1}, detach=True)

    exit_code = main(["task", "wait", str(task.id), "--json", "--quiet"])

    out, err = capsys.readouterr()
    assert (exit_code, json.loads(out), err) == (0, {"waited_seconds": 1.0}, "")


def diagnose_parser() -> Parser:
    """A command that launches the diagnostic task, as process, suggest and render will."""
    parser, commands = create_parser()
    command = add_command(
        commands,
        "diagnose",
        help="diagnóstico",
        run=lambda args, ctx: launch(
            ctx,
            args.wait,
            partial(
                start,
                Home.from_environment(),
                "diagnostic",
                SERMON,
                {"seconds": args.seconds, "fail_with": args.fail_with},
            ),
        ),
        render=json.dumps,
    )
    add_wait_option(command)
    command.add_argument("--seconds", type=float, default=0)
    command.add_argument("--fail-with")
    return parser


def diagnose(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any, str]:
    exit_code = execute(diagnose_parser(), ["diagnose", "--json", *argv])
    out, err = capsys.readouterr()
    return exit_code, json.loads(out), err


def test_launch_without_wait_answers_at_once_with_the_running_task(
    wordcut_home: Path, detached_tasks: DetachedTasks, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer, _ = diagnose(["--seconds", "5"], capsys)

    assert (exit_code, answer) == (
        0,
        {"task_id": answer["task_id"], "kind": "diagnostic", "status": "running", "sermon_id": 12},
    )


def test_launch_with_wait_runs_here_with_progress_on_stderr_and_the_result_on_stdout(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer, err = diagnose(["--seconds", "0.3", "--wait"], capsys)

    [task] = list_tasks(Home(wordcut_home))["items"]
    assert (exit_code, answer, err.splitlines()[-1], task["pid"]) == (
        0,
        {"waited_seconds": 0.3},
        "[diagnostic] pronto 100%",
        os.getpid(),
    )


def test_launch_with_wait_of_a_failing_task_exits_with_its_error_code(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer, _ = diagnose(["--wait", "--fail-with", "sermon_too_short"], capsys)

    assert (exit_code, answer["error"]["code"]) == (5, "sermon_too_short")


def test_ctrl_c_in_launch_with_wait_interrupts_the_task_and_exits_130(
    wordcut_home: Path, time_limit: None, capsys: pytest.CaptureFixture[str]
) -> None:
    home = Home(wordcut_home)

    with ctrl_c_after(0.3):
        exit_code = execute(diagnose_parser(), ["diagnose", "--wait", "--seconds", "10"])

    [task] = list_tasks(home)["items"]
    assert (exit_code, task["status"], task["error"]["code"], ProcessingLock(home).holder()) == (
        130,
        "failed",
        "interrupted",
        None,
    )


def test_quiet_launch_with_wait_prints_no_progress(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer, err = diagnose(["--seconds", "0.3", "--wait", "--quiet"], capsys)

    assert (exit_code, answer, err) == (0, {"waited_seconds": 0.3}, "")


def test_launch_while_the_machine_is_busy_exits_4_without_a_task(
    wordcut_home: Path, lock_owner: StartLockOwner, capsys: pytest.CaptureFixture[str]
) -> None:
    lock_owner("render", "cut 34")

    exit_code, answer, _ = diagnose([], capsys)

    assert (exit_code, answer["error"]["code"], list_tasks(Home(wordcut_home))["items"]) == (
        4,
        "busy",
        [],
    )
