import argparse
import json
import subprocess
from collections.abc import Callable
from importlib.metadata import version
from typing import Any

import pytest

from wordcut.errors import WordcutError
from wordcut.home import Home
from wordcut.lock import ProcessingLock
from wordcut_cli import main
from wordcut_cli.contract import Context, add_command, create_parser, execute

Run = Callable[[argparse.Namespace, Context], dict[str, Any]]


def cli_with(run: Run) -> Callable[[list[str]], int]:
    parser, commands = create_parser()
    add_command(commands, "probe", help="comando de teste", run=run, render=lambda _: "pronto")
    return lambda argv: execute(parser, argv)


def answer(result: dict[str, Any]) -> Run:
    return lambda args, ctx: result


def fail_with(error: BaseException) -> Run:
    def run(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
        raise error

    return run


MISSING_SERMON = WordcutError("not_found", "Pregação 7 não existe.", {"sermon_id": 7})


def test_json_option_after_the_command_prints_the_result_as_one_json_document(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_with(answer({"answer": "sim"}))(["probe", "--json"])

    assert (exit_code, json.loads(capsys.readouterr().out)) == (0, {"answer": "sim"})


def test_without_json_the_result_is_printed_as_readable_text(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli_with(answer({"answer": "sim"}))(["probe"])

    assert capsys.readouterr().out == "pronto\n"


def test_json_option_before_the_command_gives_the_same_output_as_after(
    capsys: pytest.CaptureFixture[str],
) -> None:
    run = cli_with(answer({"answer": "sim"}))
    outputs = []
    for argv in (["--json", "probe"], ["probe", "--json"]):
        outputs.append((run(argv), capsys.readouterr().out))

    assert outputs[0] == outputs[1]


@pytest.mark.parametrize("argv", [["--json", "--quiet", "probe"], ["--json", "probe", "--quiet"]])
def test_quiet_option_reaches_the_handler_before_or_after_the_command(
    argv: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    cli_with(lambda args, ctx: {"quiet": ctx.quiet})(argv)

    assert json.loads(capsys.readouterr().out) == {"quiet": True}


def test_domain_error_with_json_prints_only_the_error_object_and_exits_with_its_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_with(fail_with(MISSING_SERMON))(["--json", "probe"])

    assert (exit_code, json.loads(capsys.readouterr().out)) == (
        3,
        {
            "error": {
                "code": "not_found",
                "message": "Pregação 7 não existe.",
                "details": {"sermon_id": 7},
            }
        },
    )


def test_domain_error_without_json_leaves_stdout_empty_and_writes_the_message_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_with(fail_with(MISSING_SERMON))(["probe"])

    captured = capsys.readouterr()
    assert (exit_code, captured.out, captured.err) == (3, "", "erro: Pregação 7 não existe.\n")


def test_unexpected_failure_becomes_internal_error_without_any_traceback(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("WORDCUT_DEBUG", raising=False)

    exit_code = cli_with(fail_with(RuntimeError("segredo interno")))(["--json", "probe"])

    captured = capsys.readouterr()
    assert (exit_code, json.loads(captured.out), captured.err) == (
        1,
        {"error": {"code": "internal_error", "message": "Erro interno inesperado."}},
        "",
    )


def test_debug_mode_writes_the_traceback_to_stderr_and_keeps_stdout_clean(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WORDCUT_DEBUG", "1")

    cli_with(fail_with(RuntimeError("falha de depuração")))(["--json", "probe"])

    captured = capsys.readouterr()
    assert (json.loads(captured.out)["error"]["code"], "Traceback" in captured.err) == (
        "internal_error",
        True,
    )


def test_ctrl_c_exits_with_130_and_prints_no_result(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli_with(fail_with(KeyboardInterrupt()))(["--json", "probe"])

    assert (exit_code, capsys.readouterr().out) == (130, "")


def test_unknown_option_with_json_is_an_invalid_argument_error_in_portuguese(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_with(answer({}))(["probe", "--bogus", "--json"])

    assert (exit_code, json.loads(capsys.readouterr().out)) == (
        2,
        {
            "error": {
                "code": "invalid_argument",
                "message": "Argumento não reconhecido: --bogus.",
                "details": {"argument": "--bogus"},
            }
        },
    )


def test_missing_command_names_the_missing_argument(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli_with(answer({}))(["--json"])

    assert (exit_code, json.loads(capsys.readouterr().out)["error"]) == (
        2,
        {
            "code": "invalid_argument",
            "message": "Argumento obrigatório ausente: command.",
            "details": {"argument": "command"},
        },
    )


def run_with_count_option(argv: list[str]) -> int:
    parser, commands = create_parser()
    probe = add_command(commands, "probe", help="comando de teste", run=answer({}), render=str)
    probe.add_argument("--count", type=int)
    return execute(parser, argv)


def test_malformed_value_names_the_argument_it_belongs_to(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_with_count_option(["--json", "probe", "--count", "muitos"])

    assert (exit_code, json.loads(capsys.readouterr().out)["error"]) == (
        2,
        {
            "code": "invalid_argument",
            "message": "Valor inválido para --count: 'muitos'.",
            "details": {"argument": "--count"},
        },
    )


def test_option_without_its_value_names_the_argument(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = run_with_count_option(["--json", "probe", "--count"])

    assert (exit_code, json.loads(capsys.readouterr().out)["error"]) == (
        2,
        {
            "code": "invalid_argument",
            "message": "Uso inválido de --count.",
            "details": {"argument": "--count"},
        },
    )


def test_usage_error_without_json_leaves_stdout_empty_and_explains_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_with(answer({}))(["probe", "--bogus"])

    captured = capsys.readouterr()
    assert (exit_code, captured.out, captured.err) == (
        2,
        "",
        "erro: Argumento não reconhecido: --bogus.\n",
    )


def test_version_prints_the_installed_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--version"])

    assert (exit_code, capsys.readouterr().out) == (0, f"{version('wordcut-cli')}\n")


def take_the_processing_lock(args: argparse.Namespace, ctx: Context) -> dict[str, Any]:
    with ProcessingLock(Home.from_environment()).acquire("process", "sermon 12"):
        return {"done": True}


def test_command_refused_by_a_lock_held_elsewhere_exits_with_busy_and_the_holder(
    lock_owner: Callable[[str, str], subprocess.Popen[str]], capsys: pytest.CaptureFixture[str]
) -> None:
    owner = lock_owner("render", "cut 34")

    exit_code = cli_with(take_the_processing_lock)(["--json", "probe"])

    error = json.loads(capsys.readouterr().out)["error"]
    assert (exit_code, error["code"], error["details"]["pid"], error["details"]["kind"]) == (
        4,
        "busy",
        owner.pid,
        "render",
    )
