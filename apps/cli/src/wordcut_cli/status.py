"""``wordcut status``: whether the machine is free or which operation holds it (docs/cli.md §10)."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any

from wordcut.home import Home
from wordcut.service.status import machine_status
from wordcut_cli.contract import Context, add_command
from wordcut_cli.tasks_support import percent, resource_label

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands


def register(commands: Commands) -> None:
    add_command(
        commands,
        "status",
        help="estado da máquina: livre ou qual tarefa segura a trava, e as tarefas em andamento",
        run=_run,
        render=_render,
        example="wordcut status --json",
    )


def _run(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    return machine_status(Home.from_environment())


def _render(result: dict[str, Any]) -> str:
    return "\n".join([_render_lock(result["lock"]), *_render_running(result["running_tasks"])])


def _render_lock(lock: dict[str, Any]) -> str:
    if not lock["held"]:
        return "Máquina livre: nenhum processamento em andamento."
    known = {field: "?" if value is None else value for field, value in lock.items()}
    task = "" if lock["task_id"] is None else f"tarefa {lock['task_id']}, "
    return (
        f"Máquina ocupada: {task}{known['kind']} de {known['resource']} (PID {known['pid']}),"
        f" desde {known['started_at']}, há {known['elapsed_seconds']} s."
    )


def _render_running(running: list[dict[str, Any]]) -> list[str]:
    if not running:
        return []
    return ["Tarefas em andamento:"] + [
        f"  {task['id']}  {task['kind']}  {resource_label(task)}  {percent(task['progress'])}"
        for task in running
    ]
