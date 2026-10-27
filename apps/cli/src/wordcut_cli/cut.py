"""``wordcut cut <action>``: see and preview the suggested cuts of a sermon, create one,
choose, discard or restore them, fix the spelling of their caption words, set their caption
style, set what they play, resize or move their range, export and delete them (docs/cli.md
§8.1–§8.11)."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections.abc import Callable
from contextlib import closing
from dataclasses import fields
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wordcut.cuts.caption import POSITIONS, RANGES, SHADOWS, CaptionSettings
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.rendering.options import CHOICES
from wordcut.service.cuts import (
    caption_of,
    choose_cut,
    create_cut,
    delete_cut,
    discard_cut,
    fix_word,
    list_cuts,
    move_range,
    preview_cut,
    reset_caption,
    restore_cut,
    set_range,
    set_segments,
    show_cut,
    update_caption,
)
from wordcut.service.rendering import estimate_render, show_render, start_render
from wordcut.service.sermons import CUT_STATES
from wordcut.timefmt import format_timestamp, parse_timestamp
from wordcut_cli import deps
from wordcut_cli.contract import Context, add_command, add_group
from wordcut_cli.tasks_support import add_wait_option, launch

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands

CAPTION_FIELDS = tuple(field.name for field in fields(CaptionSettings))
POSITION_NAMES = {"top": "topo", "center": "centro", "bottom": "base"}
SHADOW_NAMES = {"none": "nenhuma", "soft": "suave", "strong": "forte"}
STDIN = "-"
STATE_NAMES = {"suggested": "sugerido", "chosen": "escolhido", "discarded": "descartado"}


def register(commands: Commands) -> None:
    actions = add_group(
        commands,
        "cut",
        help="cortes: ver, criar, escolher, descartar, restaurar, corrigir a grafia, definir os"
        " trechos, ajustar a faixa, ajustar o estilo da legenda e exportar",
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
    create = add_command(
        actions,
        "create",
        help="cria um corte do zero com todas as frases da faixa, encostada em início e fim de"
        " frase, já escolhido — administrador",
        run=_create,
        render=_render_cut,
        example='wordcut cut create --sermon 12 --start 12:30 --end 13:30 --title "Graça" --json',
    )
    create.add_argument("--sermon", type=int, required=True, help="ID da pregação")
    create.add_argument(
        "--start",
        type=parse_timestamp,
        required=True,
        help="início na pregação, SS, MM:SS ou HH:MM:SS",
    )
    create.add_argument(
        "--end", type=parse_timestamp, required=True, help="fim na pregação, SS, MM:SS ou HH:MM:SS"
    )
    create.add_argument(
        "--title", help='título do corte; sem ele, "Novo corte · MM:SS" do início na pregação'
    )
    segments = add_command(
        actions,
        "segments",
        help="define o que entra no corte e em que ordem: uma lista JSON de trechos"
        ' [{"from_word", "to_word"}], dentro da faixa e sem sobreposição — administrador',
        run=_segments,
        render=_render_cut,
        example="wordcut cut segments 34 --file - --json < trechos.json",
    )
    segments.add_argument("id", type=int, help="ID do corte")
    segments.add_argument(
        "--file", required=True, help="arquivo com a lista de trechos, em JSON; - lê do stdin"
    )
    resize = add_command(
        actions,
        "range",
        help="redimensiona a faixa do corte, encostando em início e fim de frase; as palavras"
        " que ficam de fora saem do corte — administrador",
        run=_range_command,
        render=_render_cut,
        example="wordcut cut range 34 --start 1:02:10 --end 1:03:05 --json",
    )
    resize.add_argument("id", type=int, help="ID do corte")
    resize.add_argument(
        "--start", type=parse_timestamp, help="início na pregação, SS, MM:SS ou HH:MM:SS"
    )
    resize.add_argument(
        "--end", type=parse_timestamp, help="fim na pregação, SS, MM:SS ou HH:MM:SS"
    )
    move = add_command(
        actions,
        "move",
        help="desloca a faixa inteira em segundos, sem sair da pregação; as frases escolhidas"
        " acompanham e encostam na frase mais próxima — administrador",
        run=_move_command,
        render=_render_cut,
        example="wordcut cut move 34 --by -12.5 --json",
    )
    move.add_argument("id", type=int, help="ID do corte")
    move.add_argument(
        "--by", type=float, required=True, help="deslocamento em segundos; negativo volta"
    )
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
    export = add_command(
        actions,
        "render",
        help="exporta o corte em 9:16 (tarefa com trava); as opções ficam salvas no corte, e a"
        " omitida usa a última salva",
        run=_render,
        render=_render_export,
        example="wordcut cut render 34 --pauses short --no-fade --wait --json",
    )
    export.add_argument("id", type=int, help="ID do corte")
    _add_render_options(export)
    delete = add_command(
        actions,
        "delete",
        help=(
            "apaga o corte com suas exportações e arquivos, sem pedir confirmação; recusa com"
            " busy enquanto ele exporta ou a pregação dele processa ou sugere — administrador"
        ),
        run=_delete,
        render=_render_deleted,
        example="wordcut cut delete 34 --json",
    )
    delete.add_argument("id", type=int, help="ID do corte")


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


# docs/cli.md §8.7: each switch, its help when on and its help when off.
RENDER_SWITCHES = {
    "smooth_joins": ("suaviza as emendas", "emendas secas"),
    "fade": ("fade no início e no fim", "sem fade"),
    "normalize": ("áudio normalizado a -14 LUFS", "áudio sem normalizar"),
    "caption": ("com legenda, como cut caption --on", "sem legenda, como cut caption --off"),
}
RENDER_CHOICE_HELP = {
    "fillers": "hesitações (hã, né)",
    "stammers": "gaguejos e frases recomeçadas",
    "pauses": "pausas",
    "resolution": "resolução do vídeo",
    "quality": "qualidade: alta ou arquivo menor",
}
RENDER_OPTIONS = (*RENDER_CHOICE_HELP, *RENDER_SWITCHES)


def _add_render_options(export: argparse.ArgumentParser) -> None:
    for name, help_text in RENDER_CHOICE_HELP.items():
        export.add_argument(f"--{name}", choices=CHOICES[name], help=help_text)
    for name, (on, off) in RENDER_SWITCHES.items():
        flag = name.replace("_", "-")
        switch = export.add_mutually_exclusive_group()
        switch.add_argument(f"--{flag}", dest=name, action="store_const", const=True, help=on)
        switch.add_argument(f"--no-{flag}", dest=name, action="store_const", const=False, help=off)
    export.add_argument(
        "--estimate",
        action="store_true",
        help="só calcula a duração e mostra as opções, sem exportar, sem salvar e sem a trava",
    )
    add_wait_option(export)


def _render(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    """The launched task; with ``--wait``, the export (docs/cli.md §9); with ``--estimate``, the
    estimated duration and the options, outside the lock."""
    changes = {
        name: getattr(args, name) for name in RENDER_OPTIONS if getattr(args, name) is not None
    }
    if args.estimate:
        if args.wait:
            raise WordcutError(
                "invalid_argument",
                "--estimate não cria tarefa; não use --wait com ele.",
                {"argument": "--wait"},
            )
        with closing(deps.connection()) as connection:
            return estimate_render(connection, args.id, changes)
    home = Home.from_environment()
    launched = launch(ctx, args.wait, partial(start_render, home, args.id, changes))
    if not args.wait:
        return launched
    with closing(deps.connection()) as connection:
        return show_render(connection, home, launched["render_id"])


RENDER_CHOICE_NAMES = {
    "remove": "remover",
    "keep": "manter",
    "original": "originais",
    "natural": "naturais",
    "short": "curtas",
    "high": "alta",
    "small": "arquivo menor",
}
RENDER_OPTION_NAMES = {
    "fillers": "Hesitações",
    "stammers": "Gaguejos",
    "pauses": "Pausas",
    "smooth_joins": "Emendas suavizadas",
    "fade": "Fade",
    "normalize": "Normalizar áudio",
    "caption": "Legenda",
    "resolution": "Resolução",
    "quality": "Qualidade",
}


def _render_export(result: dict[str, Any]) -> str:
    if "task_id" in result:
        return (
            f"Tarefa {result['task_id']} iniciada: exportação do corte {result['cut_id']}."
            f" Acompanhe com wordcut task wait {result['task_id']}."
        )
    if "id" not in result:
        return "\n".join(
            [f"Duração estimada: {_seconds(result['duration'])}", *_option_lines(result)]
        )
    return describe_export(result)


def describe_export(export: dict[str, Any]) -> str:
    """The export as ``render show`` gives it, in readable text (docs/cli.md §9)."""
    return "\n".join(
        [
            f"Exportação {export['id']} do corte {export['cut_id']}: {export['path']}",
            f"Duração: {_seconds(export['duration'])}",
            *_option_lines(export),
        ]
    )


def _option_lines(result: dict[str, Any]) -> list[str]:
    return [
        f"{RENDER_OPTION_NAMES[name]}: {_option_value(value)}"
        for name, value in result["options"].items()
    ]


def _option_value(value: Any) -> str:
    if isinstance(value, bool):
        return "sim" if value else "não"
    return RENDER_CHOICE_NAMES.get(value, str(value))


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


def _delete(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return delete_cut(Home.from_environment(), connection, args.id)


def _render_deleted(result: dict[str, Any]) -> str:
    return f"Corte {result['id']} apagado, com suas exportações."


def _show(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return show_cut(connection, args.id, home=Home.from_environment())


def _preview(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return preview_cut(connection, args.id)


def _fix_word(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return fix_word(connection, args.id, args.word_id, args.text)


def _segments(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    wanted = _segments_file(args.file)
    with closing(deps.connection()) as connection:
        try:
            return set_segments(connection, args.id, wanted)
        except WordcutError as error:
            if (error.details or {}).get("argument") != "segments":
                raise
            raise WordcutError(error.code, error.message, {"argument": "file"}) from error


def _create(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return create_cut(connection, args.sermon, args.start, args.end, args.title)


def _range_command(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return set_range(connection, args.id, args.start, args.end)


def _move_command(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return move_range(connection, args.id, args.by)


def _segments_file(source: str) -> list[Any]:
    """The list of segments in ``source``, a path or ``-`` for the standard input."""
    # ADR-0015: neither the path nor the content the user gave is repeated.
    try:
        text = sys.stdin.read() if source == STDIN else Path(source).read_text(encoding="utf-8")
        wanted = json.loads(text)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise _unreadable_segments() from error
    if not isinstance(wanted, list):
        raise _unreadable_segments()
    return wanted


def _unreadable_segments() -> WordcutError:
    return WordcutError(
        "invalid_argument",
        "Não foi possível ler os trechos; use um arquivo JSON com uma lista de"
        ' {"from_word", "to_word"}.',
        {"argument": "file"},
    )


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
