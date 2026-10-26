"""Output and error contract shared by every ``wordcut`` command (docs/cli.md §3.2, §4, §5).

A command is a pure handler ``run(args, ctx) -> dict`` plus a ``render(result) -> str`` for
readable text. The contract parses the global options, prints the result as JSON or text
and turns failures into the error object and the exit code.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import version
from typing import TYPE_CHECKING, Any, NoReturn

from wordcut.errors import WordcutError

JSON_OPTION = "--json"

# docs/cli.md §5.1: shell convention for a process interrupted by SIGINT (128 + 2).
INTERRUPTED_EXIT_CODE = 130

Result = dict[str, Any]


class Parser(argparse.ArgumentParser):
    """Parser whose usage errors are ``invalid_argument`` errors instead of an exit."""

    def error(self, message: str) -> NoReturn:
        raise _usage_error(message)


if TYPE_CHECKING:
    Commands = argparse._SubParsersAction[Parser]


# CPython's argparse reports usage errors only as English text; these patterns follow the
# messages of Lib/argparse.py and name the offending argument in the group "argument".
_USAGE_ERRORS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"the following arguments are required: (?P<argument>[^,]+)"),
        "Argumento obrigatório ausente: {argument}.",
    ),
    (
        re.compile(r"unrecognized arguments: (?P<argument>\S+)"),
        "Argumento não reconhecido: {argument}.",
    ),
    (
        re.compile(
            r"argument (?P<argument>[^:]+): invalid (?:choice|\S+ value): (?P<value>'[^']*')"
        ),
        "Valor inválido para {argument}: {value}.",
    ),
    (re.compile(r"argument (?P<argument>[^:]+): "), "Uso inválido de {argument}."),
)


def _usage_error(message: str) -> WordcutError:
    """Translate an argparse usage message into the ``invalid_argument`` error."""
    for pattern, template in _USAGE_ERRORS:
        match = pattern.match(message)
        if match:
            return WordcutError(
                "invalid_argument",
                template.format(**match.groupdict()),
                {"argument": match["argument"]},
            )
    return WordcutError("invalid_argument", "Uso inválido; veja wordcut --help.")


@dataclass(frozen=True)
class Context:
    json: bool
    quiet: bool

    def warn(self, message: str) -> None:
        """Tell the user on stderr; ``--quiet`` silences progress only, never a warning."""
        print(f"aviso: {message}", file=sys.stderr)


Handler = Callable[[argparse.Namespace, Context], Result]
Renderer = Callable[[Result], str]


@dataclass(frozen=True)
class Command:
    run: Handler
    render: Renderer


def create_parser() -> tuple[Parser, Commands]:
    parser = Parser(
        prog="wordcut",
        description="Da live do culto à pregação recortada e aos cortes verticais.",
    )
    parser.add_argument(
        "--version", action="version", version=version("wordcut-cli"), help="mostra a versão"
    )
    _add_global_options(parser, default=False)
    commands = parser.add_subparsers(dest="command", required=True)
    return parser, commands


def add_group(commands: Commands, name: str, *, help: str) -> Commands:
    """A resource whose actions are added with ``add_command`` (``wordcut <name> <ação>``)."""
    group = commands.add_parser(name, help=help, description=help)
    _add_global_options(group, default=argparse.SUPPRESS)
    return group.add_subparsers(dest="action", required=True)


def add_command(
    commands: Commands,
    name: str,
    *,
    help: str,
    run: Handler,
    render: Renderer,
    example: str | None = None,
) -> Parser:
    command = commands.add_parser(
        name,
        help=help,
        description=help,
        epilog=f"Exemplo:\n  {example}" if example else None,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_global_options(command, default=argparse.SUPPRESS)
    command.set_defaults(contract=Command(run, render))
    return command


def _add_global_options(parser: argparse.ArgumentParser, default: Any) -> None:
    # The command repeats the root options with a suppressed default so that an option
    # given before the command is not reset to False by the command's own parser.
    parser.add_argument(JSON_OPTION, action="store_true", default=default, help="saída em JSON")
    parser.add_argument(
        "--quiet", action="store_true", default=default, help="suprime o progresso no stderr"
    )


def execute(parser: argparse.ArgumentParser, argv: list[str]) -> int:
    """Parse ``argv``, run the chosen command and return the process exit code."""
    try:
        args = parser.parse_args(argv)
    except SystemExit as stop:
        return int(stop.code or 0)
    except WordcutError as error:
        return _report(error, as_json=JSON_OPTION in argv)
    command: Command | None = getattr(args, "contract", None)
    if command is None:
        # Commands of the previous CLI (wordcut_cli.legacy) keep their own output and runtime
        # errors until the cli-migration roadmap item; their usage errors follow the contract.
        args.handler(args)
        return 0
    return _run(command, args, Context(json=args.json, quiet=args.quiet))


def _run(command: Command, args: argparse.Namespace, ctx: Context) -> int:
    try:
        result = command.run(args, ctx)
        print(json.dumps(result, ensure_ascii=False) if ctx.json else command.render(result))
    except KeyboardInterrupt:
        return INTERRUPTED_EXIT_CODE
    except WordcutError as error:
        return _report(error, as_json=ctx.json)
    except Exception:
        if os.environ.get("WORDCUT_DEBUG") == "1":
            traceback.print_exc(file=sys.stderr)
        return _report(WordcutError("internal_error", "Erro interno inesperado."), as_json=ctx.json)
    return 0


def _report(error: WordcutError, *, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"error": error.to_dict()}, ensure_ascii=False))
    else:
        print(f"erro: {error.message}", file=sys.stderr)
    return error.exit_code
