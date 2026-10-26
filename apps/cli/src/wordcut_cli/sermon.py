"""``wordcut sermon <action>``: create, list and show sermons (docs/cli.md §7)."""

from __future__ import annotations

import argparse
from contextlib import closing
from datetime import date
from typing import TYPE_CHECKING, Any

from wordcut.errors import WordcutError
from wordcut.service.sermons import (
    SERMON_STATES,
    create_sermon,
    list_sermons,
    show_sermon,
    trim_sermon,
)
from wordcut.timefmt import parse_timestamp
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
TIME_HELP = "em tempo da live: HH:MM:SS[.mmm], MM:SS[.mmm] ou segundos"


def register(commands: Commands) -> None:
    actions = add_group(commands, "sermon", help="pregações: criar, listar e detalhar")
    create = add_command(
        actions,
        "create",
        help=(
            "cria a pregação a partir do link da live e mostra título, data e duração;"
            " com --start e --end, já a delimita"
        ),
        run=_create,
        render=_render_created,
        example="wordcut sermon create https://youtu.be/Ab3_x-9QzLk --json",
    )
    create.add_argument("link", help="link do vídeo da live no YouTube")
    _add_borders(create, required=False)
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
    trim = add_command(
        actions,
        "trim",
        help="define as bordas da pregação, em tempo da live",
        run=_trim,
        render=_render_shown,
        example="wordcut sermon trim 12 --start 1:02:10 --end 1:48:30 --json",
    )
    trim.add_argument("id", type=int, help="ID da pregação")
    _add_borders(trim, required=True)


def _add_borders(command: argparse.ArgumentParser, *, required: bool) -> None:
    command.add_argument(
        "--start", type=parse_timestamp, required=required, help=f"início, {TIME_HELP}"
    )
    command.add_argument("--end", type=parse_timestamp, required=required, help=f"fim, {TIME_HELP}")


def _create(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    _require_both_borders(args)
    with closing(deps.connection()) as connection:
        sermon = create_sermon(
            connection, deps.live_source(), args.link, start=args.start, end=args.end
        )
    _warn_if_reprocess_needed(sermon, ctx)
    if not sermon["live_finished"]:
        ctx.warn("A live ainda não terminou; a pregação foi criada mesmo assim.")
    return sermon


def _require_both_borders(args: argparse.Namespace) -> None:
    """Name the missing option as the other usage errors do (docs/cli.md §5.2)."""
    if (args.start is None) != (args.end is None):
        given, missing = ("--end", "--start") if args.start is None else ("--start", "--end")
        raise WordcutError("invalid_argument", f"{given} exige {missing}.", {"argument": missing})


def _list(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return list_sermons(connection, args.status)


def _show(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return show_sermon(connection, args.id)


def _trim(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        sermon = trim_sermon(connection, args.id, args.start, args.end)
    _warn_if_reprocess_needed(sermon, ctx)
    return sermon


def _warn_if_reprocess_needed(sermon: dict[str, Any], ctx: Context) -> None:
    """Take the service's ``needs_reprocess`` out of the answer, which keeps show's format."""
    if sermon.pop("needs_reprocess", False):
        ctx.warn(
            "A pregação já foi processada; as bordas novas valem depois de"
            " wordcut sermon process --force."
        )


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
