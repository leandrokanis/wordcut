import pytest

from wordcut_cli import main

COMMANDS = "{info,transcribe,transcribe-live,overview,cut,preview,short,sermon,status}"


def test_help_lists_every_command(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["--help"])

    assert (exit_code, COMMANDS in capsys.readouterr().out) == (0, True)
