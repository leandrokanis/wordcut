"""``wordcut settings <action>``: models, LLM key and YouTube cookies (docs/cli.md §11.1)."""

from __future__ import annotations

import argparse
import getpass
import sys
from contextlib import closing
from typing import TYPE_CHECKING, Any

from wordcut.db import connect
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.settings import (
    show_settings,
    store_llm_key,
    store_youtube_cookies,
    update_settings,
)
from wordcut_cli.contract import Context, add_command, add_group

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands


def register(commands: Commands) -> None:
    actions = add_group(
        commands,
        "settings",
        help="configurações do LLM, da transcrição e dos segredos — administrador",
    )
    add_command(
        actions,
        "show",
        help="mostra os modelos, a chave do LLM mascarada e se há cookies — administrador",
        run=_show,
        render=_render,
        example="wordcut settings show --json",
    )
    change = add_command(
        actions,
        "set",
        help="troca o modelo do LLM, o do WhisperX ou os dois — administrador",
        run=_set,
        render=_render,
        example="wordcut settings set --model <id do OpenRouter> --whisper-model large-v3",
    )
    change.add_argument("--model", help="modelo do LLM, como o OpenRouter o identifica")
    change.add_argument("--whisper-model", help="modelo do WhisperX da transcrição")
    add_command(
        actions,
        "set-key",
        help=(
            "grava a chave do LLM, lida só do stdin; no terminal, digitada sem eco — administrador"
        ),
        run=_set_key,
        render=_render,
        example="wordcut settings set-key < chave.txt",
    )
    add_command(
        actions,
        "set-cookies",
        help=(
            "grava os cookies do YouTube (formato Netscape), lidos só do stdin redirecionado"
            " — administrador"
        ),
        run=_set_cookies,
        render=_render,
        example="wordcut settings set-cookies < cookies.txt",
    )


def _show(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return show_settings(connection)


def _set(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return update_settings(connection, llm_model=args.model, whisper_model=args.whisper_model)


def _set_key(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    typed = sys.stdin.isatty()
    store_llm_key(getpass.getpass("Chave do LLM: ") if typed else sys.stdin.read())
    return _show(args, ctx)


def _set_cookies(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    # getpass reads one line, and a cookie file has many: the file must come redirected.
    if sys.stdin.isatty():
        raise WordcutError(
            "invalid_argument",
            "Redirecione o arquivo de cookies para o stdin:"
            " wordcut settings set-cookies < cookies.txt",
            {"argument": "stdin"},
        )
    store_youtube_cookies(sys.stdin.read())
    return _show(args, ctx)


def _render(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Modelo do LLM: {result['llm_model'] or 'não escolhido'}",
            f"Modelo do WhisperX: {result['whisper_model']}",
            f"Chave do LLM: {result['llm_key'] or 'não gravada'}",
            f"Cookies do YouTube: {'gravados' if result['youtube_cookies'] else 'não gravados'}",
            f"Preset padrão: {result['default_preset_id']}",
        ]
    )
