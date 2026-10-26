"""``wordcut cut <action>``: see and preview the suggested cuts of a sermon and choose,
discard or restore them (docs/cli.md §8.1–§8.4)."""

from __future__ import annotations

import argparse
import sqlite3
from collections.abc import Callable
from contextlib import closing
from functools import partial
from typing import TYPE_CHECKING, Any

from wordcut.service.cuts import (
    choose_cut,
    discard_cut,
    list_cuts,
    preview_cut,
    restore_cut,
    show_cut,
)
from wordcut.service.sermons import CUT_STATES
from wordcut.timefmt import format_timestamp
from wordcut_cli import deps
from wordcut_cli.contract import Context, add_command, add_group

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands

STATE_NAMES = {"suggested": "sugerido", "chosen": "escolhido", "discarded": "descartado"}


def register(commands: Commands) -> None:
    actions = add_group(commands, "cut", help="cortes: ver, escolher, descartar e restaurar")
    listing = add_command(
        actions,
        "list",
        help="lista os cortes da pregação com texto montado, duração e estado;"
        " descartados por último",
        run=_list,
        render=_render_list,
        example="wordcut cut list --sermon 12 --json",
    )
    listing.add_argument("--sermon", type=int, required=True, help="ID da pregação")
    listing.add_argument("--status", choices=CUT_STATES, help="só os cortes neste estado")
    show = add_command(
        actions,
        "show",
        help="mostra o corte completo: texto montado, duração, estado, faixa na pregação,"
        " trechos com tempos e texto, palavras, legenda e exportações",
        run=_show,
        render=_render_cut,
        example="wordcut cut show 34 --json",
    )
    show.add_argument("id", type=int, help="ID do corte")
    preview = add_command(
        actions,
        "preview",
        help="mostra a sequência que a prévia toca: cada trecho com início e fim na pregação"
        " e o texto, marcando com ↑ o que volta no tempo; nunca espera a trava",
        run=_preview,
        render=_render_preview,
        example="wordcut cut preview 34 --json",
    )
    preview.add_argument("id", type=int, help="ID do corte")
    for name, change, help_text in (
        ("choose", choose_cut, "marca o corte como escolhido; não muda o conteúdo"),
        ("discard", discard_cut, "descarta o corte; não muda o conteúdo"),
        (
            "restore",
            restore_cut,
            "devolve o corte descartado a sugerido; não muda o conteúdo",
        ),
    ):
        transition = add_command(
            actions,
            name,
            help=help_text,
            run=partial(_change, change),
            render=_render_cut,
            example=f"wordcut cut {name} 34 --json",
        )
        transition.add_argument("id", type=int, help="ID do corte")


def _list(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return list_cuts(connection, args.sermon, args.status)


def _show(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return show_cut(connection, args.id)


def _preview(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return preview_cut(connection, args.id)


def _change(
    change: Callable[[sqlite3.Connection, int], dict[str, Any]],
    args: argparse.Namespace,
    ctx: Context,
) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return change(connection, args.id)


def _render_cut(cut: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Corte {cut['id']}: {cut['title']}",
            f"Estado: {STATE_NAMES[cut['status']]}",
            f"Duração: {_seconds(cut['duration'])}",
            f"Faixa na pregação: palavras {cut['range_start_word']} a {cut['range_end_word']}",
            "Trechos:",
            *(
                f"  {format_timestamp(segment['start'])} a {format_timestamp(segment['end'])}"
                f"  {segment['text']}"
                for segment in cut["segments"]
            ),
            f"Texto: {cut['text']}",
        ]
    )


def _render_preview(preview: dict[str, Any]) -> str:
    return "\n".join(_preview_line(segment) for segment in preview["segments"])


def _preview_line(segment: dict[str, Any]) -> str:
    times = f"[{format_timestamp(segment['start'])} → {format_timestamp(segment['end'])}]"
    jump = "↑ " if segment["out_of_order"] else ""
    return f"{times} {jump}{segment['text']}"


def _render_list(result: dict[str, Any]) -> str:
    return "\n".join(_listed_line(item) for item in result["items"]) or "Nenhum corte."


def _listed_line(cut: dict[str, Any]) -> str:
    state, duration = STATE_NAMES[cut["status"]], _seconds(cut["duration"])
    return f"{cut['id']}  {state}  {duration}  {cut['title']}"


def _seconds(duration: float) -> str:
    return f"{duration:.1f} s".replace(".", ",")
