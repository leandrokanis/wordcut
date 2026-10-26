import json

import pytest

from wordcut_cli import main

NEW_COMMANDS = [
    "criteria",
    "cut",
    "member",
    "preset",
    "render",
    "sermon",
    "settings",
    "status",
    "task",
]
COMMANDS = "{" + ",".join(NEW_COMMANDS) + "}"
PREVIOUS_CLI_COMMANDS = [
    "info",
    "transcribe",
    "transcribe-live",
    "overview",
    "cut-sermon",
    "preview",
    "short",
]


def test_help_lists_every_command(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--help"])

    assert (exit_code, COMMANDS in capsys.readouterr().out) == (0, True)


@pytest.mark.parametrize("name", PREVIOUS_CLI_COMMANDS)
def test_a_command_of_the_previous_cli_is_an_invalid_argument(
    name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["--json", name])

    error = json.loads(capsys.readouterr().out)["error"]
    assert (exit_code, error["code"], error["details"]["choices"]) == (
        2,
        "invalid_argument",
        NEW_COMMANDS,
    )


@pytest.mark.parametrize("group", [name for name in NEW_COMMANDS if name != "status"])
def test_group_help_fits_an_80_column_terminal(
    group: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("COLUMNS", "80")

    main([group, "--help"])

    assert max(len(line) for line in capsys.readouterr().out.splitlines()) <= 80


def test_command_help_fits_an_80_column_terminal(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("COLUMNS", "80")

    main(["sermon", "download", "--help"])

    assert max(len(line) for line in capsys.readouterr().out.splitlines()) <= 80


def test_help_keeps_the_example_on_its_own_line(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("COLUMNS", "80")

    main(["member", "--help"])

    assert "Exemplo:\n  wordcut member add assistente@exemplo.org --role assistant\n" in (
        capsys.readouterr().out
    )
