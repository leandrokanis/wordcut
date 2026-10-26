import pytest

from wordcut_cli import main

COMMANDS = "{info,transcribe,transcribe-live,overview,cut,preview,short}"


def test_help_lists_every_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])

    assert COMMANDS in capsys.readouterr().out
