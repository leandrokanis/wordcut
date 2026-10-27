import json
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.home import Home
from wordcut.processing.sentences import split_sentences
from wordcut.service.cuts import move_range
from wordcut.transcript import Word
from wordcut_cli import main

NOW = datetime(2026, 10, 27, 3, 0, tzinfo=timezone.utc)
# Eight sentences of two words; sentence k spans 10k to 10k + 8 s.
SPOKEN = tuple(
    word
    for k in range(8)
    for word in (Word("Frase", 10.0 * k, 10.0 * k + 4), Word(f"{k}.", 10.0 * k + 4.5, 10.0 * k + 8))
)


def cut_over_the_first_five_sentences(youtube_id: str = "Ab3_x-9QzLk") -> tuple[int, list[int]]:
    """A cut playing sentences 1 to 3 over the range of sentences 0 to 4 of a processed
    ``SPOKEN`` sermon, its ID and the IDs of the sermon's words."""
    with closing(connect(Home.from_environment())) as connection, connection:
        sermon = sermons.insert(
            connection,
            NewSermon(
                youtube_id=youtube_id,
                url=f"https://youtu.be/{youtube_id}",
                title="Culto de domingo",
                service_date=date(2026, 10, 18),
                live_duration=7718.0,
                live_finished=True,
                created_at=NOW,
            ),
        )
        transcripts.replace(connection, sermon.id, SPOKEN, split_sentences(SPOKEN))
        word = [row.id for row in transcripts.words_of(connection, sermon.id)]
        new = NewCut(
            "suggested", "Graça", (Segment(word[2], word[7]),), word[0], word[9], "llm", None
        )
        [cut_id] = cuts.insert_many(connection, sermon.id, [new], NOW)
        return cut_id, word


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_cut_range_resizes_the_range_and_prints_the_cut_as_cut_show_does(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, word = cut_over_the_first_five_sentences()

    answer = run_json(
        ["cut", "range", str(cut_id), "--start", "17", "--end", "0:41", "--json"], capsys
    )

    shown = run_json(["cut", "show", str(cut_id), "--json"], capsys)
    assert (answer, (shown[1]["range_start_word"], shown[1]["range_end_word"])) == (
        shown,
        (word[4], word[7]),
    )


@pytest.mark.parametrize("by", [["--by", "-10"], ["--by=-10"]])
def test_cut_move_takes_a_negative_shift_and_gives_what_the_service_gives(
    by: list[str], wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, _ = cut_over_the_first_five_sentences()
    twin_id, _ = cut_over_the_first_five_sentences("Zz9_y-8PqRs")
    with closing(connect(Home.from_environment())) as connection:
        twin = move_range(connection, twin_id, -10.0)

    exit_code, answer = run_json(["cut", "move", str(cut_id), *by, "--json"], capsys)

    assert (exit_code, timed(answer)) == (0, timed(twin))


def timed(cut: dict[str, Any]) -> list[tuple[float, float, str]]:
    """What the cut plays, by time and text, to compare cuts of different sermons."""
    return [(segment["start"], segment["end"], segment["text"]) for segment in cut["segments"]]


REFUSED = {
    "shorter than 10 s": ["range", "--start", "19", "--end", "31"],
    "end before the start": ["range", "--start", "40", "--end", "20"],
    "no border": ["range"],
    "no chosen sentence left": ["range", "--start", "50", "--end", "78"],
}


@pytest.mark.parametrize("case", list(REFUSED))
def test_a_refused_range_exits_2_and_stores_nothing(
    case: str, wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, _ = cut_over_the_first_five_sentences()
    _, before = run_json(["cut", "show", str(cut_id), "--json"], capsys)
    action, *options = REFUSED[case]

    exit_code, answer = run_json(["cut", action, str(cut_id), *options, "--json"], capsys)

    assert (
        exit_code,
        answer["error"]["code"],
        answer["error"]["details"],
        run_json(["cut", "show", str(cut_id), "--json"], capsys)[1],
    ) == (2, "invalid_argument", {"argument": "range"}, before)


@pytest.mark.parametrize("action", [["range", "--start", "0"], ["move", "--by", "5"]])
def test_changing_the_range_of_a_cut_that_does_not_exist_exits_3(
    action: list[str], wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(["cut", action[0], "999", *action[1:], "--json"], capsys)

    assert (exit_code, answer["error"]["code"]) == (3, "not_found")


def test_cut_move_without_by_exits_2(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, _ = cut_over_the_first_five_sentences()

    exit_code, answer = run_json(["cut", "move", str(cut_id), "--json"], capsys)

    assert (exit_code, answer["error"]["code"]) == (2, "invalid_argument")
