import json
from pathlib import Path

import pytest

from wordcut.sermon import CutResult
from wordcut.sermon_folder import SermonFolder
from wordcut.transcript import Transcript, Word
from wordcut_cli import legacy, main


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


def test_previous_cut_command_is_now_cut_sermon_and_still_cuts_and_reports_the_sermon(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[tuple[str, Path, float, float]] = []

    def cut_without_youtube_nor_ffmpeg(
        youtube: object, url: str, folder: SermonFolder, first_word: float, last_word: float
    ) -> CutResult:
        asked.append((url, folder.path, first_word, last_word))
        return CutResult(live_start=3729.7, live_end=6512.5, section_offset_error=0.25, words=6418)

    monkeypatch.setattr(legacy, "cut_sermon", cut_without_youtube_nor_ffmpeg)
    folder = tmp_path / "2026-10-18 - Graça - Ef 2"

    exit_code = main(
        ["cut-sermon", "https://youtu.be/Ab3_x-9QzLk", "--dir", str(folder),
         "--first-word", "1:02:10", "--last-word", "1:48:31"]
    )  # fmt: skip

    assert (exit_code, asked, capsys.readouterr().out) == (
        0,
        [("https://youtu.be/Ab3_x-9QzLk", folder, 3730.0, 6511.0)],
        "pregação: 01:02:09.700 -> 01:48:32.500 na live (00:46:22.800)\n"
        "desvio do download: +0.250 s\n"
        f"{folder / '2026-10-18 - Graça - Ef 2.mp4'}\n"
        f"{folder / 'palavras.json'} (6418 palavras)\n",
    )
