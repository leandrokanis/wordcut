"""``wordcut task <action>``: list, show and wait for tasks (docs/cli.md §6, §10)."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any

from wordcut.home import Home
from wordcut.service.tasks import TASK_KINDS, TASK_STATES, list_tasks, show_task, wait_task
from wordcut_cli.contract import Context, add_command, add_group
from wordcut_cli.tasks_support import percent, progress_printer, render_result, resource_label

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands

STATE_NAMES = {"running": "em andamento", "succeeded": "concluída", "failed": "falhou"}


def register(commands: Commands) -> None:
    actions = add_group(commands, "task", help="tarefas: listar, detalhar e esperar")
    listing = add_command(
        actions,
        "list",
        help="lista as tarefas, da mais recente para a mais antiga",
        run=_list,
        render=_render_listed,
        example="wordcut task list --status running --json",
    )
    listing.add_argument("--status", choices=TASK_STATES, help="só as tarefas neste estado")
    listing.add_argument("--kind", choices=TASK_KINDS, help="só as tarefas deste tipo")
    show = add_command(
        actions,
        "show",
        help="mostra a tarefa: tipo, estado, recurso, início, fim, progresso, erro e resultado",
        run=_show,
        render=_render_shown,
        example="wordcut task show 9 --json",
    )
    show.add_argument("id", type=int, help="ID da tarefa")
    wait = add_command(
        actions,
        "wait",
        help=(
            "espera a tarefa terminar, com o progresso no stderr, e sai como ela;"
            " Ctrl+C só para a espera"
        ),
        run=_wait,
        render=render_result,
        example="wordcut task wait 9 --json",
    )
    wait.add_argument("id", type=int, help="ID da tarefa")


def _list(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    return list_tasks(Home.from_environment(), args.status, args.kind)


def _show(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    return show_task(Home.from_environment(), args.id)


def _wait(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    return wait_task(Home.from_environment(), args.id, on_progress=progress_printer(ctx))


def _render_listed(result: dict[str, Any]) -> str:
    lines = [
        f"{item['id']}  {STATE_NAMES[item['status']]}  {item['kind']}  {resource_label(item)}"
        f"  {percent(item['progress'])}"
        for item in result["items"]
    ]
    return "\n".join(lines) or "Nenhuma tarefa."


def _render_shown(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Tarefa {result['id']}: {result['kind']} de {resource_label(result)}",
            f"Estado: {STATE_NAMES[result['status']]}",
            f"Progresso: {percent(result['progress'])} {result['progress_message'] or ''}".rstrip(),
            f"Início: {result['started_at']}",
            f"Fim: {result['finished_at'] or '—'}",
            f"Erro: {result['error']['message'] if result['error'] else '—'}",
        ]
    )
