"""``wordcut sermon <action>``: create, list and show sermons (docs/cli.md §7)."""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date
from typing import TYPE_CHECKING, Any

from wordcut.service.sermons import (
    SERMON_STATES,
    create_sermon,
    list_sermons,
    show_sermon,
)
from wordcut_cli import deps
from wordcut_cli.contract import Context, add_command, add_group

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands

STATE_NAMES = {
    "created": "criada",
    "trimmed": "delimitada",
    "processing": "processando",
    "processed": "processada",
    "failed": "falhou",
}


def register(commands: Commands) -> None:
    actions = add_group(commands, "sermon", help="pregações: criar, listar e detalhar")
    create = add_command(
        actions,
        "create",
        help="cria a pregação a partir do link da live e mostra título, data e duração",
        run=_create,
        render=_render_created,
        example="wordcut sermon create https://youtu.be/Ab3_x-9QzLk --json",
    )
    create.add_argument("link", help="link do vídeo da live no YouTube")
    listing = add_command(
        actions,
        "list",
        help="lista as pregações, da mais recente para a mais antiga",
        run=_list,
        render=_render_listed,
        example="wordcut sermon list --status created --json",
    )
    listing.add_argument("--status", choices=SERMON_STATES, help="só as pregações neste estado")
    show = add_command(
        actions,
        "show",
        help="mostra a pregação, suas bordas na live e seus cortes",
        run=_show,
        render=_render_shown,
        example="wordcut sermon show 12 --json",
    )
    show.add_argument("id", type=int, help="ID da pregação")


def _create(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        sermon = create_sermon(connection, deps.live_source(), args.link)
    if not sermon["live_finished"]:
        ctx.warn("A live ainda não terminou; a pregação foi criada mesmo assim.")
    return sermon


def _list(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return list_sermons(connection, args.status)


def _show(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return show_sermon(connection, args.id)


def _render_created(result: dict[str, Any]) -> str:
    outcome = "criada" if result["created"] else "já existia"
    return (
        f"Pregação {result['id']} {outcome}: {result['title']},"
        f" culto de {_service_date(result)}, live de {_live_duration(result)}."
    )


def _render_listed(result: dict[str, Any]) -> str:
    lines = [
        f"{item['id']}  {_service_date(item)}  {STATE_NAMES[item['status']]}  {item['title']}"
        for item in result["items"]
    ]
    return "\n".join(lines) or "Nenhuma pregação."


def _render_shown(result: dict[str, Any]) -> str:
    situation = "terminada" if result["live_finished"] else "ainda no ar"
    return "\n".join(
        [
            f"Pregação {result['id']}: {result['title']}",
            f"Culto: {_service_date(result)}",
            f"Live: {_live_duration(result)}, {situation}",
            f"Estado: {STATE_NAMES[result['status']]}",
            f"Bordas: {_borders(result)}",
            f"Cortes: {len(result['cuts']) or 'nenhum'}",
        ]
    )


def _borders(sermon: dict[str, Any]) -> str:
    if sermon["live_start"] is None or sermon["live_end"] is None:
        return "não definidas"
    return f"{_clock(sermon['live_start'])} a {_clock(sermon['live_end'])} da live"


def _service_date(sermon: dict[str, Any]) -> str:
    return date.fromisoformat(sermon["service_date"]).strftime("%d/%m/%Y")


def _live_duration(sermon: dict[str, Any]) -> str:
    seconds = sermon["live_duration"]
    return "duração desconhecida" if seconds is None else _clock(seconds)


def _clock(seconds: float) -> str:
    minutes, second = divmod(round(seconds), 60)
    hour, minute = divmod(minutes, 60)
    return f"{hour}:{minute:02d}:{second:02d}"
