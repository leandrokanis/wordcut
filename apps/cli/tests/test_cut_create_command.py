import json
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, sermons, transcripts
from wordcut.db.sermons import NewSermon
from wordcut.home import Home
from wordcut.processing.sentences import split_sentences
from wordcut.transcript import Word
from wordcut_cli import main

NOW = datetime(2026, 10, 27, 3, 0, tzinfo=timezone.utc)
# Eight sentences of two words; sentence k spans 10k to 10k + 8 s of an 80 s sermon.
SPOKEN = tuple(
    word
    for k in range(8)
    for word in (Word("Frase", 10.0 * k, 10.0 * k + 4), Word(f"{k}.", 10.0 * k + 4.5, 10.0 * k + 8))
)


def sermon_of_spoken(processed: bool = True) -> tuple[int, list[int]]:
    """A ``SPOKEN`` sermon, processed unless told otherwise, its ID and its words' IDs."""
    with closing(connect(Home.from_environment())) as connection, connection:
        sermon = sermons.insert(
            connection,
            NewSermon(
                youtube_id="Ab3_x-9QzLk",
                url="https://youtu.be/Ab3_x-9QzLk",
                title="Culto de domingo",
                service_date=date(2026, 10, 18),
                live_duration=7718.0,
                live_finished=True,
                created_at=NOW,
            ),
        )
        transcripts.replace(connection, sermon.id, SPOKEN, split_sentences(SPOKEN))
        if processed:
            sermons.record_processed(connection, sermon.id, 1000.0, 1080.0, "sermon.mp4", NOW)
        return sermon.id, [row.id for row in transcripts.words_of(connection, sermon.id)]


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_cut_create_creates_a_chosen_admin_cut_and_prints_it_as_cut_show_does(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id, word = sermon_of_spoken()

    exit_code, answer = run_json(
        [
            "cut", "create", "--sermon", str(sermon_id),
            "--start", "17", "--end", "0:41", "--title", "Graça", "--json",
        ],
        capsys,
    )  # fmt: skip

    shown = run_json(["cut", "show", str(answer["id"]), "--json"], capsys)
    assert (
        (exit_code, answer),
        (answer["status"], answer["source"], answer["title"]),
        (answer["range_start_word"], answer["range_end_word"]),
    ) == (shown, ("chosen", "admin", "Graça"), (word[4], word[7]))


REFUSED: dict[str, tuple[bool, list[str], int, str]] = {
    "shorter than 10 s": (True, ["--start", "19", "--end", "31"], 2, "invalid_argument"),
    "end before the start": (True, ["--start", "40", "--end", "20"], 2, "invalid_argument"),
    "outside the sermon": (True, ["--start", "50", "--end", "81"], 2, "invalid_argument"),
    "not processed": (False, ["--start", "17", "--end", "41"], 5, "sermon_not_processed"),
}


@pytest.mark.parametrize("case", list(REFUSED))
def test_a_refused_cut_create_exits_with_the_contract_code_and_creates_nothing(
    case: str, wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    processed, options, code, error = REFUSED[case]
    sermon_id, _ = sermon_of_spoken(processed)

    exit_code, answer = run_json(
        ["cut", "create", "--sermon", str(sermon_id), *options, "--json"], capsys
    )

    assert (
        exit_code,
        answer["error"]["code"],
        run_json(["cut", "list", "--sermon", str(sermon_id), "--json"], capsys)[1],
    ) == (code, error, {"items": []})


def test_cut_create_on_a_sermon_that_does_not_exist_exits_3(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(
        ["cut", "create", "--sermon", "999", "--start", "17", "--end", "41", "--json"], capsys
    )

    assert (exit_code, answer["error"]["code"]) == (3, "not_found")


def test_cut_create_without_json_prints_the_new_cut_with_its_default_title(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id, _ = sermon_of_spoken()

    exit_code = main(["cut", "create", "--sermon", str(sermon_id), "--start", "17", "--end", "41"])

    printed = capsys.readouterr().out
    assert (exit_code, printed.splitlines()[:2]) == (
        0,
        ["Corte 1: Novo corte · 00:20", "Estado: escolhido"],
    )
