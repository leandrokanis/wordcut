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
from wordcut.transcript import Word
from wordcut_cli import main

NOW = datetime(2026, 10, 26, 22, 40, tzinfo=timezone.utc)
SPOKEN = (
    Word("Irmãos,", 0.3, 0.8),
    Word("Jesús", 0.9, 1.2),
    Word("não", 1.25, 1.3),
    Word("falha.", 1.35, 1.9),
    Word("Deus", 2.5, 2.8),
    Word("governa.", 2.85, 3.4),
)


def cut_playing(*spans: tuple[int, int]) -> tuple[int, list[int]]:
    """A cut of a processed ``SPOKEN`` sermon that plays the words at positions ``first`` to
    ``last`` of each span, in that order, its ID and the IDs of the sermon's words."""
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
        return cut_id, word


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_fix_word_with_json_prints_the_fixed_word_with_its_cut_and_exits_0(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, word = cut_playing((0, 3))

    answer = run_json(["cut", "fix-word", str(cut_id), str(word[1]), "Jesus", "--json"], capsys)

    assert answer == (
        0,
        {
            "cut_id": cut_id,
            "word_id": word[1],
            "text": "Jesús",
            "start": 0.9,
            "end": 1.2,
            "corrected": "Jesus",
        },
    )


def test_fix_word_that_changes_the_word_is_too_different_exits_5_and_says_how_far(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, word = cut_playing((0, 3))

    exit_code, answer = run_json(
        ["cut", "fix-word", str(cut_id), str(word[2]), "sim", "--json"], capsys
    )

    error = answer["error"]
    assert (exit_code, error["code"], error["details"], "sim" in error["message"]) == (
        5,
        "spelling_too_different",
        {"distance": 3, "limit": 1, "original": "não"},
        False,
    )


@pytest.mark.parametrize(
    ("word_position", "text", "argument"),
    [(4, "Deus", "word_id"), (1, "Jesus Cristo", "text"), (1, "   ", "text")],
)
def test_fix_word_of_a_word_out_of_the_cut_or_a_text_that_is_not_one_word_exits_2(
    word_position: int,
    text: str,
    argument: str,
    wordcut_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cut_id, word = cut_playing((0, 3))

    exit_code, answer = run_json(
        ["cut", "fix-word", str(cut_id), str(word[word_position]), text, "--json"], capsys
    )

    error = answer["error"]
    assert (exit_code, error["code"], error["details"], text.strip() in error["message"]) == (
        2,
        "invalid_argument",
        {"argument": argument},
        text.strip() == "",
    )


def test_fix_word_with_a_word_id_that_is_not_a_number_exits_2_without_echoing_it(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(["cut", "fix-word", "1", "doze", "Jesus", "--json"], capsys)

    error = answer["error"]
    assert (exit_code, error["details"], "doze" in error["message"]) == (
        2,
        {"argument": "word_id"},
        False,
    )


def test_fix_word_of_a_cut_that_does_not_exist_is_not_found_and_exits_3(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code, answer = run_json(["cut", "fix-word", "999", "1", "Jesus", "--json"], capsys)

    assert (exit_code, answer["error"]["code"], answer["error"]["details"]) == (
        3,
        "not_found",
        {"cut_id": 999},
    )


def test_fix_word_back_to_the_original_removes_the_fix(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, word = cut_playing((0, 3))
    main(["cut", "fix-word", str(cut_id), str(word[1]), "Jesus"])
    capsys.readouterr()

    answer = run_json(["cut", "fix-word", str(cut_id), str(word[1]), "Jesús", "--json"], capsys)

    assert (answer[0], answer[1]["corrected"]) == (0, None)


@pytest.mark.parametrize(
    "argv",
    [
        ["--json", "cut", "fix-word", "1", "2", "Jesus"],
        ["cut", "--json", "fix-word", "1", "2", "Jesus"],
        ["cut", "fix-word", "1", "2", "Jesus", "--json"],
    ],
)
def test_json_option_is_accepted_before_between_and_after_the_fix_word_action(
    argv: list[str], wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_playing((0, 3))

    exit_code, fixed = run_json(argv, capsys)

    assert (exit_code, fixed["corrected"]) == (0, "Jesus")


def test_fix_word_without_json_prints_one_line_with_the_word_its_original_and_its_fix(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, word = cut_playing((0, 3))

    exit_code = main(["cut", "fix-word", str(cut_id), str(word[1]), "Jesus"])

    out = capsys.readouterr().out
    assert (exit_code, len(out.splitlines()), out.startswith("{")) == (0, 1, False)
    assert all(part in out for part in (str(word[1]), "Jesús", "Jesus"))


def test_fix_word_without_json_says_the_error_on_stderr_only(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, word = cut_playing((0, 3))

    exit_code = main(["cut", "fix-word", str(cut_id), str(word[2]), "sim"])

    out, err = capsys.readouterr()
    assert (exit_code, out, err != "") == (5, "", True)


def test_after_fix_word_cut_show_and_preview_carry_the_fixed_spelling(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cut_id, word = cut_playing((4, 5), (0, 1))
    main(["cut", "fix-word", str(cut_id), str(word[1]), "Jesus"])
    capsys.readouterr()

    _, shown = run_json(["cut", "show", str(cut_id), "--json"], capsys)
    _, preview = run_json(["cut", "preview", str(cut_id), "--json"], capsys)
    main(["cut", "preview", str(cut_id)])
    readable = capsys.readouterr().out

    assert (shown["text"], preview["segments"][1]["text"], "Irmãos, Jesus" in readable) == (
        "Deus governa. Irmãos, Jesus",
        "Irmãos, Jesus",
        True,
    )
