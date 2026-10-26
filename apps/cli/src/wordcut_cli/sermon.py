"""``wordcut sermon <action>``: create, list, show, trim, process, download and suggest the
cuts of sermons (docs/cli.md §7)."""

from __future__ import annotations

import argparse
import os
from contextlib import closing
from datetime import date
from functools import partial
from typing import TYPE_CHECKING, Any

from wordcut.errors import WordcutError
from wordcut.files import copy_without_overwrite
from wordcut.home import Home
from wordcut.service.processing import start_processing
from wordcut.service.sermons import (
    SERMON_STATES,
    create_sermon,
    list_sermons,
    sermon_video,
    show_sermon,
    trim_sermon,
)
from wordcut.service.suggestion import start_suggestion
from wordcut.timefmt import format_timestamp, parse_timestamp
from wordcut_cli import deps
from wordcut_cli.contract import Context, add_command, add_group
from wordcut_cli.tasks_support import add_wait_option, launch

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
            " com --start e --end, já a delimita; com --process, em seguida a processa"
        ),
        run=_create,
        render=_render_created_or_processing,
        example="wordcut sermon create https://youtu.be/Ab3_x-9QzLk --json",
    )
    create.add_argument("link", help="link do vídeo da live no YouTube")
    _add_borders(create, required=False)
    create.add_argument(
        "--process",
        action="store_true",
        help="em seguida processa a pregação, como sermon process; exige --start e --end",
    )
    add_wait_option(create)
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
    show.add_argument(
        "--transcript",
        action="store_true",
        help=(
            "acrescenta a transcrição: uma frase por linha, com ID, tempo da pregação e IDs da"
            " primeira e da última palavra"
        ),
    )
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
    process = add_command(
        actions,
        "process",
        help=(
            "processa a pregação delimitada: baixa só a faixa, transcreve, corta em 16:9 e"
            " grava palavras e frases"
        ),
        run=_process,
        render=_render_processing,
        example="wordcut sermon process 12 --wait --json",
    )
    process.add_argument("id", type=int, help="ID da pregação")
    process.add_argument(
        "--force",
        action="store_true",
        help="processa de novo uma pregação já processada, descartando palavras, frases e cortes",
    )
    add_wait_option(process)
    download = add_command(
        actions,
        "download",
        help=(
            "copia o vídeo 16:9 da pregação processada para o caminho indicado, ou para a pasta"
            " atual com nome legível (data e título), sem sobrescrever; mostra o caminho"
        ),
        run=_download,
        render=_render_downloaded,
        example="wordcut sermon download 12 -o ~/Vídeos/ --json",
    )
    download.add_argument("id", type=int, help="ID da pregação")
    suggest = add_command(
        actions,
        "suggest",
        help=(
            "pede ao LLM nova sugestão de cortes da pregação processada, com o preset indicado"
            " ou o padrão; troca os cortes sugeridos não editados e mantém escolhidos,"
            " descartados e editados — administrador"
        ),
        run=_suggest,
        render=_render_suggestion,
        example="wordcut sermon suggest 12 --preset 3 --wait --json",
    )
    suggest.add_argument("id", type=int, help="ID da pregação")
    suggest.add_argument("--preset", type=int, help="ID do preset; padrão: o preset padrão")
    add_wait_option(suggest)
    download.add_argument(
        "-o",
        "--output",
        default=os.curdir,
        help=(
            "arquivo de destino, ou pasta (existente ou terminada em /) que recebe o nome"
            " legível; padrão: a pasta atual"
        ),
    )


def _add_borders(command: argparse.ArgumentParser, *, required: bool) -> None:
    command.add_argument(
        "--start", type=parse_timestamp, required=required, help=f"início, {TIME_HELP}"
    )
    command.add_argument("--end", type=parse_timestamp, required=required, help=f"fim, {TIME_HELP}")


def _create(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    _require_both_borders(args)
    _require_what_processing_needs(args)
    with closing(deps.connection()) as connection:
        sermon = create_sermon(
            connection, deps.live_source(), args.link, start=args.start, end=args.end
        )
    _warn_if_reprocess_needed(sermon, ctx)
    if not sermon["live_finished"]:
        ctx.warn("A live ainda não terminou; a pregação foi criada mesmo assim.")
    if not args.process:
        return sermon
    return _processing(ctx, sermon["id"], force=False, wait=args.wait)


def _require_both_borders(args: argparse.Namespace) -> None:
    """Name the missing option as the other usage errors do (docs/cli.md §5.2)."""
    if (args.start is None) != (args.end is None):
        given, missing = ("--end", "--start") if args.start is None else ("--start", "--end")
        raise WordcutError("invalid_argument", f"{given} exige {missing}.", {"argument": missing})


def _require_what_processing_needs(args: argparse.Namespace) -> None:
    """``--process`` needs the borders, and ``--wait`` waits only for the processing."""
    if args.wait and not args.process:
        raise WordcutError("invalid_argument", "--wait exige --process.", {"argument": "--process"})
    if args.process and args.start is None:
        raise WordcutError(
            "invalid_argument",
            "--process exige --start e --end.",
            {"argument": "--start"},
        )


def _list(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return list_sermons(connection, args.status, home=Home.from_environment())


def _show(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return show_sermon(
            connection, args.id, home=Home.from_environment(), transcript=args.transcript
        )


def _trim(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        sermon = trim_sermon(connection, args.id, args.start, args.end)
    _warn_if_reprocess_needed(sermon, ctx)
    return sermon


def _process(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    return _processing(ctx, args.id, force=args.force, wait=args.wait)


def _processing(ctx: Context, sermon_id: int, *, force: bool, wait: bool) -> dict[str, Any]:
    """The launched task, or with ``wait`` the processed sermon as ``show`` gives it."""
    home = Home.from_environment()
    start = partial(start_processing, home, sermon_id, live=deps.live_source(), force=force)
    launched = launch(ctx, wait, start)
    if not wait:
        return launched
    with closing(deps.connection()) as connection:
        return show_sermon(connection, sermon_id, home=home)


def _suggest(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    """The launched task, or with ``wait`` the new suggestion (docs/cli.md §7.6)."""
    start = partial(start_suggestion, Home.from_environment(), args.id, args.preset)
    return launch(ctx, args.wait, start)


def _download(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    """Copy outside the processing lock: reading a finished video races with nothing."""
    with closing(deps.connection()) as connection:
        video = sermon_video(connection, Home.from_environment(), args.id)
    copied = copy_without_overwrite(video.path, args.output, video.suggested_name)
    return {"path": str(copied), "bytes": copied.stat().st_size}


def _warn_if_reprocess_needed(sermon: dict[str, Any], ctx: Context) -> None:
    """Take the service's ``needs_reprocess`` out of the answer, which keeps show's format."""
    if sermon.pop("needs_reprocess", False):
        ctx.warn(
            "A pregação já foi processada; as bordas novas valem depois de"
            " wordcut sermon process --force."
        )


def _render_created_or_processing(result: dict[str, Any]) -> str:
    return _render_created(result) if "created" in result else _render_processing(result)


def _render_created(result: dict[str, Any]) -> str:
    outcome = "criada" if result["created"] else "já existia"
    return (
        f"Pregação {result['id']} {outcome}: {result['title']},"
        f" culto de {_service_date(result)}, live de {_live_duration(result)}."
    )


def _render_processing(result: dict[str, Any]) -> str:
    if "task_id" not in result:
        return _render_shown(result)
    return (
        f"Tarefa {result['task_id']} iniciada: processamento da pregação {result['sermon_id']}."
        f" Acompanhe com wordcut task wait {result['task_id']}."
    )


def _render_suggestion(result: dict[str, Any]) -> str:
    if "task_id" in result:
        return (
            f"Tarefa {result['task_id']} iniciada: sugestão de cortes da pregação"
            f" {result['sermon_id']}. Acompanhe com wordcut task wait {result['task_id']}."
        )
    suggested = result["suggested_cuts"]
    count = "1 corte sugerido" if len(suggested) == 1 else f"{len(suggested)} cortes sugeridos"
    lines = [
        f"{count} para a pregação {result['sermon_id']} com o preset {result['preset_id']}.",
        *(f"{cut['id']}  {cut['title']}" for cut in suggested),
        *(warning["message"] for warning in result["suggestion_warnings"]),
    ]
    return "\n".join(lines)


def _render_downloaded(result: dict[str, Any]) -> str:
    return str(result["path"])


def _render_listed(result: dict[str, Any]) -> str:
    lines = [
        f"{item['id']}  {_service_date(item)}  {STATE_NAMES[item['status']]}  {item['title']}"
        for item in result["items"]
    ]
    return "\n".join(lines) or "Nenhuma pregação."


def _render_shown(result: dict[str, Any]) -> str:
    situation = "terminada" if result["live_finished"] else "ainda no ar"
    lines = [
        f"Pregação {result['id']}: {result['title']}",
        f"Culto: {_service_date(result)}",
        f"Live: {_live_duration(result)}, {situation}",
        f"Estado: {STATE_NAMES[result['status']]}",
        f"Bordas: {_borders(result)}",
        f"Cortes: {len(result['cuts']) or 'nenhum'}",
    ]
    if result["suggestion_error"] is not None:
        lines.append(f"Sugestão de cortes falhou: {result['suggestion_error']['message']}")
    if "sentences" in result:
        lines += ["Transcrição:", *(_sentence_line(item) for item in result["sentences"])]
    return "\n".join(lines)


def _sentence_line(sentence: dict[str, Any]) -> str:
    return (
        f"{sentence['id']}  {format_timestamp(sentence['start'])}  {sentence['text']}"
        f"  (palavras {sentence['first_word_id']}–{sentence['last_word_id']})"
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
