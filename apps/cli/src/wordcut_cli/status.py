"""``wordcut status``: whether the machine is free or which operation holds it (docs/cli.md §10)."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any

from wordcut.home import Home
from wordcut.service.status import machine_status
from wordcut_cli.contract import Context, add_command

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands


def register(commands: Commands) -> None:
    add_command(
        commands,
        "status",
        help="estado da máquina: livre ou qual processamento segura a trava",
        run=_run,
        render=_render,
        example="wordcut status --json",
    )


def _run(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    return machine_status(Home.from_environment())


def _render(result: dict[str, Any]) -> str:
    lock = result["lock"]
    if not lock["held"]:
        return "Máquina livre: nenhum processamento em andamento."
    known = {field: "?" if value is None else value for field, value in lock.items()}
    return (
        f"Máquina ocupada: {known['kind']} de {known['resource']} (PID {known['pid']}),"
        f" desde {known['started_at']}, há {known['elapsed_seconds']} s."
    )
