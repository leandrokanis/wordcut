"""``wordcut render <action>``: list, show and download the exports of a cut (docs/cli.md §9)."""

from __future__ import annotations

import argparse
import os
from contextlib import closing
from typing import TYPE_CHECKING, Any

from wordcut.files import copy_without_overwrite
from wordcut.home import Home
from wordcut.service.rendering import show_render
from wordcut.service.renders import list_renders, render_video
from wordcut_cli import deps
from wordcut_cli.contract import Context, add_command, add_group
from wordcut_cli.cut import describe_export

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands


def register(commands: Commands) -> None:
    actions = add_group(commands, "render", help="exportações: listar, detalhar e baixar")
    listing = add_command(
        actions,
        "list",
        help="lista as exportações do corte, da mais recente para a mais antiga",
        run=_list,
        render=_render_list,
        example="wordcut render list --cut 34 --json",
    )
    listing.add_argument("--cut", type=int, required=True, help="ID do corte")
    show = add_command(
        actions,
        "show",
        help="mostra a exportação: corte, caminho local do arquivo, duração, data e opções",
        run=_show,
        render=describe_export,
        example="wordcut render show 7 --json",
    )
    show.add_argument("id", type=int, help="ID da exportação")
    download = add_command(
        actions,
        "download",
        help=(
            "copia o vídeo da exportação para o caminho indicado, ou para a pasta atual com nome"
            " legível (data do culto e título do corte), sem sobrescrever; mostra o caminho"
        ),
        run=_download,
        render=_render_downloaded,
        example="wordcut render download 7 -o ~/Vídeos/ --json",
    )
    download.add_argument("id", type=int, help="ID da exportação")
    download.add_argument(
        "-o",
        "--output",
        default=os.curdir,
        help=(
            "arquivo de destino, ou pasta (existente ou terminada em /) que recebe o nome"
            " legível; padrão: a pasta atual"
        ),
    )


def _list(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return list_renders(connection, Home.from_environment(), args.cut)


def _show(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(deps.connection()) as connection:
        return show_render(connection, Home.from_environment(), args.id)


def _download(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    """Copy outside the processing lock: reading a finished export races with nothing."""
    with closing(deps.connection()) as connection:
        video = render_video(connection, Home.from_environment(), args.id)
    copied = copy_without_overwrite(video.path, args.output, video.suggested_name)
    return {"path": str(copied), "bytes": copied.stat().st_size}


def _render_downloaded(result: dict[str, Any]) -> str:
    return str(result["path"])


def _render_list(result: dict[str, Any]) -> str:
    return (
        "\n".join(f"{item['id']}  {item['created_at']}  {item['path']}" for item in result["items"])
        or "Nenhuma exportação."
    )
