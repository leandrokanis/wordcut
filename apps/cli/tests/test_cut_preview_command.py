import json
import re
import subprocess
from collections.abc import Callable
from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from wordcut.db import connect, cuts, sermons, transcripts
from wordcut.db.cuts import NewCut, Segment
from wordcut.db.sermons import NewSermon
from wordcut.home import Home
from wordcut.transcript import Word
from wordcut_cli import main

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
# HH:MM:SS.mmm, the time format of readable output (docs/cli.md §2).
TIMESTAMP = re.compile(r"\d\d:\d\d:\d\d\.\d{3}")
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
    Word("Deus", 2.5, 2.8),
    Word("governa.", 2.85, 3.4),
)


def cut_playing(*spans: tuple[int, int]) -> int:
    """A cut of a processed ``SPOKEN`` sermon that plays the words at positions ``first`` to
    ``last`` of each span, in that order, and its ID."""
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
        transcripts.replace(connection, sermon.id, SPOKEN, ())
        word = [row.id for row in transcripts.words_of(connection, sermon.id)]
        segments = tuple(Segment(word[first], word[last]) for first, last in spans)
        new = NewCut("suggested", "Graça que alcança", segments, word[0], word[5], "llm", None)
        [cut_id] = cuts.insert_many(connection, sermon.id, [new], NOW)
        return cut_id


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_preview_with_json_prints_the_segments_in_cut_order_marking_the_one_that_goes_back(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Late, then early (goes back in time), then between the two but after the early one.
    cut_id = cut_playing((4, 5), (0, 1), (3, 3))

    answer = run_json(["cut", "preview", str(cut_id), "--json"], capsys)

    assert answer == (
        0,
        {
            "cut_id": cut_id,
            "duration": 2.35,
            "segments": [
                {"start": 2.5, "end": 3.4, "text": "Deus governa.", "out_of_order": False},
                {"start": 0.3, "end": 1.2, "text": "Irmãos, graça", "out_of_order": True},
                {"start": 1.35, "end": 1.9, "text": "paz.", "out_of_order": False},
            ],
        },
    )


def test_preview_without_json_prints_one_line_per_segment_with_an_arrow_only_on_the_jump_back(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id = cut_playing((4, 5), (0, 1), (3, 3))

    exit_code = main(["cut", "preview", str(cut_id)])

    lines = capsys.readouterr().out.splitlines()
    assert (exit_code, [_shown(line) for line in lines]) == (
        0,
        [
            ("00:00:02.500", "00:00:03.400", "Deus governa.", False),
            ("00:00:00.300", "00:00:01.200", "Irmãos, graça", True),
            ("00:00:01.350", "00:00:01.900", "paz.", False),
        ],
    )


def _shown(line: str) -> tuple[str, str, str, bool]:
    """The start, end and text a readable preview line carries, and whether it has the arrow;
    the layout around them may change (docs/cli.md §4.2)."""
    start, end = TIMESTAMP.findall(line)
    return start, end, TIMESTAMP.sub("", line).strip(" []→↑"), "↑" in line


def test_preview_is_never_blocked_by_a_lock_held_elsewhere(
    wordcut_home: Path,
    lock_owner: Callable[[str, str], subprocess.Popen[str]],
    capsys: pytest.CaptureFixture[str],
) -> None:
    cut_id = cut_playing((4, 5), (0, 1))
    lock_owner("render", "cut 34")

    exit_code, preview = run_json(["cut", "preview", str(cut_id), "--json"], capsys)

    assert (exit_code, preview["cut_id"], len(preview["segments"])) == (0, cut_id, 2)


def test_preview_of_a_cut_that_does_not_exist_is_not_found_and_exits_3(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(["cut", "preview", "999", "--json"], capsys)

    assert (exit_code, answer["error"]["code"], answer["error"]["details"]) == (
        3,
        "not_found",
        {"cut_id": 999},
    )


def test_preview_without_json_says_the_error_on_stderr_only(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["cut", "preview", "999"])

    out, err = capsys.readouterr()
    assert (exit_code, out, err != "") == (3, "", True)


def test_preview_of_a_malformed_id_is_invalid_and_exits_2(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(["cut", "preview", "trinta", "--json"], capsys)

    assert (exit_code, answer["error"]["code"], answer["error"]["details"]) == (
        2,
        "invalid_argument",
        {"argument": "id"},
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["--json", "cut", "preview", "1"],
        ["cut", "--json", "preview", "1"],
        ["cut", "preview", "1", "--json"],
    ],
)
def test_json_option_is_accepted_before_between_and_after_the_preview_action(
    argv: list[str], wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_playing((0, 1))

    exit_code, preview = run_json(argv, capsys)

    assert (exit_code, preview["cut_id"]) == (0, 1)
