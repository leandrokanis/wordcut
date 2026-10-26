"""``wordcut criteria list``: the filters and values of the code (docs/cli.md §11.2)."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING, Any

from wordcut.service.presets import list_criteria
from wordcut_cli.contract import Context, add_command, add_group

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands

TYPE_NAMES = {"filter": "filtro", "value": "valor"}


def register(commands: Commands) -> None:
    actions = add_group(
        commands,
        "criteria",
        help="filtros e valores das sugestões, definidos no código — administrador",
    )
    add_command(
        actions,
        "list",
        help="lista ID, nome, tipo e nível padrão de cada critério, sem o texto do prompt"
        " — administrador",
        run=_list,
        render=_render,
        example="wordcut criteria list --json",
    )


def _list(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    return {"items": list_criteria()}


def _render(result: dict[str, Any]) -> str:
    return "\n".join(
        f"{item['id']}  {item['name']} ({TYPE_NAMES[item['type']]},"
        f" nível padrão {item['default_level']})"
        for item in result["items"]
    )
