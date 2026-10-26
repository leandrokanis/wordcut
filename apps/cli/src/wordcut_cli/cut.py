"""``wordcut cut <action>``: see and preview the suggested cuts of a sermon, choose, discard
or restore them, fix the spelling of their caption words and set their caption style
(docs/cli.md §8.1–§8.6)."""

from __future__ import annotations

import argparse
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import fields
from functools import partial
from typing import TYPE_CHECKING, Any

from wordcut.cuts.caption import POSITIONS, RANGES, SHADOWS, CaptionSettings
from wordcut.errors import WordcutError
from wordcut.service.cuts import (
    caption_of,
    choose_cut,
    discard_cut,
    fix_word,
    list_cuts,
    preview_cut,
    reset_caption,
    restore_cut,
    show_cut,
    update_caption,
)
from wordcut.service.sermons import CUT_STATES
from wordcut.timefmt import format_timestamp
from wordcut_cli import deps
from wordcut_cli.contract import Context, add_command, add_group

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands

CAPTION_FIELDS = tuple(field.name for field in fields(CaptionSettings))
POSITION_NAMES = {"top": "topo", "center": "centro", "bottom": "base"}
SHADOW_NAMES = {"none": "nenhuma", "soft": "suave", "strong": "forte"}
STATE_NAMES = {"suggested": "sugerido", "chosen": "escolhido", "discarded": "descartado"}


def register(commands: Commands) -> None:
    actions = add_group(
        commands,
        "cut",
        help="cortes: ver, escolher, descartar, restaurar, corrigir a grafia e ajustar o estilo"
        " da legenda",
    )
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
    fix = add_command(
        actions,
        "fix-word",
        help="corrige a grafia de uma palavra da legenda, só neste corte; só aceita uma"
        " palavra parecida com a original, e o texto original remove a correção",
        run=_fix_word,
        render=_render_fixed_word,
        example="wordcut cut fix-word 34 1204 Jesus --json",
    )
    fix.add_argument("id", type=int, help="ID do corte")
    fix.add_argument("word_id", type=int, help="ID da palavra, como no cut show")
    fix.add_argument("text", help="a palavra com a grafia corrigida")
    caption = add_command(
        actions,
        "caption",
        help="mostra ou altera o estilo da legenda do corte, que vale para todas as legendas"
        " dele; sem opções, só mostra",
        run=_caption,
        render=_render_caption,
        example='wordcut cut caption 34 --size 72 --color "#FFFFFF" --position bottom --json',
    )
    caption.add_argument("id", type=int, help="ID do corte")
    _add_caption_options(caption)


def _add_caption_options(caption: argparse.ArgumentParser) -> None:
    shown = caption.add_mutually_exclusive_group()
    shown.add_argument(
        "--on", dest="enabled", action="store_const", const=True, help="liga a legenda"
    )
    shown.add_argument(
        "--off", dest="enabled", action="store_const", const=False, help="desliga a legenda"
    )
    caption.add_argument("--font", help="fonte, uma das incluídas no pacote")
    caption.add_argument(
        "--size", type=int, help=f"tamanho em px no quadro de 1080 por 1920 ({_range('size')})"
    )
    caption.add_argument("--color", help="cor do texto, #RRGGBB")
    caption.add_argument(
        "--position", choices=tuple(POSITIONS), help="posição; leva a altura à da posição"
    )
    caption.add_argument(
        "--offset",
        type=int,
        help=f"altura do centro da legenda, em %% do quadro ({_range('offset')}); vence --position",
    )
    caption.add_argument(
        "--border", type=int, help=f"espessura do contorno em px ({_range('border')})"
    )
    caption.add_argument("--border-color", help="cor do contorno, #RRGGBB")
    caption.add_argument("--shadow", choices=SHADOWS, help="sombra")
    caption.add_argument(
        "--reset", action="store_true", help="volta ao estilo da igreja; não aceita outra opção"
    )


def _range(field: str) -> str:
    low, high = RANGES[field]
    return f"{low} a {high}"


def _caption(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    changes = {
        field: getattr(args, field) for field in CAPTION_FIELDS if getattr(args, field) is not None
    }
    if args.reset and changes:
        raise WordcutError(
            "invalid_argument",
            "Use --reset sozinho, sem outras opções de estilo.",
            {"argument": "--reset"},
        )
    with closing(deps.connection()) as connection:
        if args.reset:
            return reset_caption(connection, args.id)
        if changes:
            return update_caption(connection, args.id, changes)
        return caption_of(connection, args.id)


def _render_caption(style: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Legenda: {'ligada' if style['enabled'] else 'desligada'}",
            f"Fonte: {style['font']}, {style['size']} px",
            f"Cor: {style['color']}",
            f"Posição: {POSITION_NAMES[style['position']]}, altura {style['offset']}%",
            f"Contorno: {style['border']} px, {style['border_color']}",
            f"Sombra: {SHADOW_NAMES[style['shadow']]}",
        ]
    )


def _list(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return list_cuts(connection, args.sermon, args.status)


def _show(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return show_cut(connection, args.id)


def _preview(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return preview_cut(connection, args.id)


def _fix_word(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return fix_word(connection, args.id, args.word_id, args.text)


def _render_fixed_word(word: dict[str, Any]) -> str:
    fix = "sem correção" if word["corrected"] is None else f"corrigida para {word['corrected']}"
    return f"Palavra {word['word_id']} do corte {word['cut_id']} ({word['text']}): {fix}."


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
