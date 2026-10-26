import json
from pathlib import Path

import pytest

from wordcut.transcript import Transcript, Word
from wordcut_cli import main


def test_previous_overview_command_still_prints_the_transcript(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    words = (Word("Deus", 0.0, 0.3), Word("governa.", 0.4, 0.9))
    path = tmp_path / "palavras.json"
    Transcript(words=words, language="pt", model="test").save(path)

    exit_code = main(["overview", str(path)])

    assert (exit_code, capsys.readouterr().out) == (0, "[00:00:00.000] Deus governa.\n")


def test_previous_command_usage_error_follows_the_contract(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["overview", "--json"])

    assert (exit_code, json.loads(capsys.readouterr().out)) == (
        2,
        {
            "error": {
                "code": "invalid_argument",
                "message": "Argumento obrigatório ausente: transcript.",
                "details": {"argument": "transcript"},
            }
        },
    )
