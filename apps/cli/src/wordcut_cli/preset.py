"""``wordcut preset <action>``: presets of the cut suggestion (docs/cli.md §11.3)."""

from __future__ import annotations

import argparse
import sys
from contextlib import closing
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wordcut.db import connect
from wordcut.db.presets import SecondsRange
from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.service.presets import (
    create_preset,
    delete_preset,
    list_presets,
    parse_level,
    parse_protected_words,
    parse_seconds_range,
    set_default,
    show_preset,
    update_preset,
)
from wordcut_cli.contract import Context, add_command, add_group

if TYPE_CHECKING:
    from wordcut_cli.contract import Commands

STDIN = "-"
# docs/cli.md §5: details.argument names the option of the parser, not of the service.
PARSER_ARGUMENTS = {"instructions": "instructions_file"}


def register(commands: Commands) -> None:
    actions = add_group(commands, "preset", help="presets das sugestões de cortes — administrador")
    add_command(
        actions,
        "list",
        help="lista os presets e qual é o padrão — administrador",
        run=_list,
        render=_render_list,
        example="wordcut preset list --json",
    )
    show = add_command(
        actions,
        "show",
        help="mostra os níveis, as durações, as opções de edição e as instruções de um preset"
        " — administrador",
        run=_show,
        render=_render_preset,
        example="wordcut preset show 1 --json",
    )
    show.add_argument("id", type=int, help="ID do preset")
    create = add_command(
        actions,
        "create",
        help="cria um preset como cópia do padrão ou de outro preset — administrador",
        run=_create,
        render=_render_preset,
        example='wordcut preset create "Estudo bíblico" --from 1',
    )
    create.add_argument("name", help="nome do preset novo")
    create.add_argument("--from", dest="from_id", type=int, help="ID do preset a copiar")
    update = add_command(
        actions,
        "update",
        help="altera nome, níveis, durações, reordenação, palavras protegidas ou instruções"
        " de um preset — administrador",
        run=_update,
        render=_render_preset,
        example="wordcut preset update 2 --level allegory=strict --duration-ideal 60-75"
        " --instructions-file instrucoes.txt",
    )
    update.add_argument("id", type=int, help="ID do preset")
    update.add_argument("--name", help="nome novo")
    update.add_argument(
        "--level",
        action="append",
        help="nível de um filtro ou valor, como allegory=strict (lenient, moderate ou"
        " strict); repetível, e o último vale para o mesmo critério",
    )
    update.add_argument("--duration-ideal", help="duração ideal, <mín>-<máx> em segundos")
    update.add_argument("--duration-allowed", help="duração permitida, <mín>-<máx> em segundos")
    update.add_argument(
        "--reorder",
        action=argparse.BooleanOptionalAction,
        help="permite (ou, com --no-reorder, proíbe) reordenar trechos",
    )
    update.add_argument(
        "--protected-words", help='palavras protegidas separadas por vírgula, como "não,mas,se"'
    )
    update.add_argument(
        "--instructions-file",
        help="arquivo com as instruções adicionais, em texto livre; - lê do stdin",
    )
    make_default = add_command(
        actions,
        "set-default",
        help="torna o preset o padrão da sugestão automática — administrador",
        run=_set_default,
        render=_render_preset,
        example="wordcut preset set-default 2",
    )
    make_default.add_argument("id", type=int, help="ID do preset")
    delete = add_command(
        actions,
        "delete",
        help="apaga um preset; o padrão não pode ser apagado — administrador",
        run=_delete,
        render=_render_deleted,
        example="wordcut preset delete 2",
    )
    delete.add_argument("id", type=int, help="ID do preset")


def _list(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return {"items": list_presets(connection)}


def _show(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return show_preset(connection, args.id)


def _create(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return create_preset(connection, args.name, from_id=args.from_id)


def _update(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    levels = None if args.level is None else dict(parse_level(text) for text in args.level)
    with closing(connect(Home.from_environment())) as connection:
        try:
            return update_preset(
                connection,
                args.id,
                name=args.name,
                levels=levels,
                duration_allowed=_seconds_range(args.duration_allowed, "duration_allowed"),
                duration_ideal=_seconds_range(args.duration_ideal, "duration_ideal"),
                reorder=args.reorder,
                protected_words=(
                    None
                    if args.protected_words is None
                    else parse_protected_words(args.protected_words)
                ),
                instructions=_instructions(args.instructions_file),
            )
        except WordcutError as error:
            details = error.details or {}
            if "argument" not in details:
                raise
            renamed = {**details, "argument": _parser_names(details["argument"])}
            raise WordcutError(error.code, error.message, renamed) from error


def _parser_names(argument: str) -> str:
    """Rename the service arguments in ``argument``, one name or a list of them."""
    names = argument.split(", ")
    return ", ".join(PARSER_ARGUMENTS.get(name, name) for name in names)


def _instructions(source: str | None) -> str | None:
    if source is None:
        return None
    if source == STDIN:
        return sys.stdin.read()
    try:
        return Path(source).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        # ADR-0015: the path the user typed is not repeated.
        raise WordcutError(
            "invalid_argument",
            "Não foi possível ler o arquivo de instruções; confira o caminho e se é texto UTF-8.",
            {"argument": "instructions_file"},
        ) from error


def _set_default(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return set_default(connection, args.id)


def _delete(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with closing(connect(Home.from_environment())) as connection:
        return delete_preset(connection, args.id)


def _render_deleted(result: dict[str, Any]) -> str:
    return f"Preset {result['id']} apagado."


def _seconds_range(text: str | None, argument: str) -> SecondsRange | None:
    return None if text is None else parse_seconds_range(text, argument)


def _render_list(result: dict[str, Any]) -> str:
    return "\n".join(
        f"{item['id']}  {item['name']}{' (padrão)' if item['is_default'] else ''}"
        for item in result["items"]
    )


def _render_preset(preset: dict[str, Any]) -> str:
    allowed, ideal = preset["duration_allowed"], preset["duration_ideal"]
    levels = [f"  {criterion}: {level}" for criterion, level in preset["levels"].items()]
    return "\n".join(
        [
            f"Preset {preset['id']}: {preset['name']}{' (padrão)' if preset['is_default'] else ''}",
            "Níveis:",
            *levels,
            f"Duração permitida: {allowed['min']}–{allowed['max']} s",
            f"Duração ideal: {ideal['min']}–{ideal['max']} s",
            f"Reordenar: {'sim' if preset['reorder'] else 'não'}",
            f"Palavras protegidas: {', '.join(preset['protected_words']) or 'nenhuma'}",
            f"Instruções adicionais: {preset['instructions'] or 'nenhuma'}",
        ]
    )
