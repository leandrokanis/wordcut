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
    Word("graça", 0.9, 1.2),
    Word("e", 1.25, 1.3),
    Word("paz.", 1.35, 1.9),
    Word("Deus", 2.5, 2.8),
    Word("governa.", 2.85, 3.4),
)


def sermon_with_cuts(*states: str) -> tuple[int, list[int]]:
    """A processed sermon with one cut in each of ``states``, added in that order, and the
    IDs of the cuts. Each cut plays "Deus governa." and then "Irmãos, graça"."""
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
        segments = (Segment(word[4], word[5]), Segment(word[0], word[1]))
        new = [
            NewCut(status, f"{number} {status}", segments, word[0], word[5], "llm", None)
            for number, status in enumerate(states, start=1)
        ]
        return sermon.id, cuts.insert_many(connection, sermon.id, new, NOW)


def run_json(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, Any]:
    exit_code = main(argv)
    return exit_code, json.loads(capsys.readouterr().out)


def test_list_with_json_prints_the_items_with_text_duration_and_state_discarded_last(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id, _ = sermon_with_cuts("discarded", "chosen", "suggested")

    exit_code, listed = run_json(["cut", "list", "--sermon", str(sermon_id), "--json"], capsys)

    assert (
        exit_code,
        [
            (item["title"], item["status"], item["text"], item["duration"])
            for item in listed["items"]
        ],
    ) == (
        0,
        [
            ("2 chosen", "chosen", "Deus governa. Irmãos, graça", 1.8),
            ("3 suggested", "suggested", "Deus governa. Irmãos, graça", 1.8),
            ("1 discarded", "discarded", "Deus governa. Irmãos, graça", 1.8),
        ],
    )


def test_list_with_json_gives_each_cut_its_span_in_sermon_time(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id, _ = sermon_with_cuts("suggested")

    exit_code, listed = run_json(["cut", "list", "--sermon", str(sermon_id), "--json"], capsys)

    assert (exit_code, [(item["start"], item["end"]) for item in listed["items"]]) == (
        0,
        [(0.3, 3.4)],
    )


def test_list_by_status_keeps_only_the_cuts_in_that_state(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id, _ = sermon_with_cuts("discarded", "chosen", "suggested", "chosen")

    exit_code, listed = run_json(
        ["cut", "list", "--sermon", str(sermon_id), "--status", "chosen", "--json"], capsys
    )

    assert (exit_code, [item["title"] for item in listed["items"]]) == (
        0,
        ["2 chosen", "4 chosen"],
    )


def test_show_with_json_prints_the_whole_cut(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id, [cut_id] = sermon_with_cuts("suggested")

    exit_code, shown = run_json(["cut", "show", str(cut_id), "--json"], capsys)

    assert (exit_code, sorted(shown), shown["text"], shown["sermon_id"]) == (
        0,
        sorted(
            [
                "id", "sermon_id", "status", "title", "text", "duration", "segments",
                "range_start_word", "range_end_word", "source", "preset_id", "edited",
                "words", "caption", "render_options", "renders",
            ]
        ),
        "Deus governa. Irmãos, graça",
        sermon_id,
    )  # fmt: skip


def test_choose_discard_and_restore_change_the_state_and_keep_the_segments(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, [cut_id] = sermon_with_cuts("suggested")
    _, before = run_json(["cut", "show", str(cut_id), "--json"], capsys)

    answers = [
        run_json(["cut", action, str(cut_id), "--json"], capsys)
        for action in ("choose", "discard", "restore")
    ]

    assert [(code, cut["status"], cut["segments"]) for code, cut in answers] == [
        (0, "chosen", before["segments"]),
        (0, "discarded", before["segments"]),
        (0, "suggested", before["segments"]),
    ]


@pytest.mark.parametrize(
    ("argv", "details"),
    [
        (["cut", "list", "--sermon", "999"], {"sermon_id": 999}),
        (["cut", "show", "999"], {"cut_id": 999}),
        (["cut", "choose", "999"], {"cut_id": 999}),
        (["cut", "discard", "999"], {"cut_id": 999}),
        (["cut", "restore", "999"], {"cut_id": 999}),
    ],
)
def test_a_sermon_or_cut_that_does_not_exist_is_not_found_and_exits_3(
    argv: list[str],
    details: dict[str, int],
    wordcut_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, answer = run_json([*argv, "--json"], capsys)

    assert (exit_code, answer["error"]["code"], answer["error"]["details"]) == (
        3,
        "not_found",
        details,
    )


@pytest.mark.parametrize(
    ("argv", "details"),
    [
        (["cut", "list"], {"argument": "--sermon"}),
        (["cut", "show", "trinta"], {"argument": "id"}),
        (["cut", "choose", "trinta"], {"argument": "id"}),
        (
            ["cut", "list", "--sermon", "1", "--status", "published"],
            {"argument": "--status", "choices": ["suggested", "chosen", "discarded"]},
        ),
    ],
)
def test_missing_or_malformed_arguments_are_invalid_and_exit_2(
    argv: list[str],
    details: dict[str, Any],
    wordcut_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code, answer = run_json([*argv, "--json"], capsys)

    assert (exit_code, answer["error"]["code"], answer["error"]["details"]) == (
        2,
        "invalid_argument",
        details,
    )


@pytest.mark.parametrize(
    ("status", "action"),
    [
        ("chosen", "choose"),
        ("discarded", "discard"),
        ("suggested", "restore"),
        ("chosen", "restore"),
    ],
)
def test_a_transition_with_nothing_to_change_exits_0_with_the_cut_as_it_was(
    status: str, action: str, wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, [cut_id] = sermon_with_cuts(status)
    _, before = run_json(["cut", "show", str(cut_id), "--json"], capsys)

    answer = run_json(["cut", action, str(cut_id), "--json"], capsys)

    assert answer == (0, before)


@pytest.mark.parametrize(
    "argv",
    [
        ["--json", "cut", "show", "1"],
        ["cut", "--json", "show", "1"],
        ["cut", "show", "1", "--json"],
    ],
)
def test_json_option_is_accepted_before_between_and_after_the_cut_action(
    argv: list[str], wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_with_cuts("suggested")

    exit_code, shown = run_json(argv, capsys)

    assert (exit_code, shown["id"]) == (0, 1)


def test_list_without_json_prints_one_line_per_cut_with_state_in_portuguese_and_duration(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id, _ = sermon_with_cuts("discarded", "chosen", "suggested")

    exit_code = main(["cut", "list", "--sermon", str(sermon_id)])

    assert (exit_code, capsys.readouterr().out) == (
        0,
        "2  escolhido  1,8 s  2 chosen\n"
        "3  sugerido  1,8 s  3 suggested\n"
        "1  descartado  1,8 s  1 discarded\n",
    )


def test_list_without_json_says_so_when_the_sermon_has_no_cuts(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sermon_id, _ = sermon_with_cuts()

    exit_code = main(["cut", "list", "--sermon", str(sermon_id)])

    assert (exit_code, capsys.readouterr().out) == (0, "Nenhum corte.\n")


def test_show_without_json_prints_title_state_duration_range_segments_and_text(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, [cut_id] = sermon_with_cuts("chosen")

    exit_code = main(["cut", "show", str(cut_id)])

    assert (exit_code, capsys.readouterr().out) == (
        0,
        "Corte 1: 1 chosen\n"
        "Estado: escolhido\n"
        "Duração: 1,8 s\n"
        "Faixa na pregação: palavras 1 a 6\n"
        "Trechos:\n"
        "  00:00:02.500 a 00:00:03.400  Deus governa.\n"
        "  00:00:00.300 a 00:00:01.200  Irmãos, graça\n"
        "Texto: Deus governa. Irmãos, graça\n",
    )


def test_error_without_json_goes_to_stderr_in_portuguese_and_stdout_stays_empty(
    wordcut_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["cut", "choose", "999"])

    captured = capsys.readouterr()
    assert (exit_code, captured.out, captured.err) == (3, "", "erro: Corte 999 não existe.\n")


def test_cut_help_lists_its_actions(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["cut", "--help"])

    assert (
        exit_code,
        "{list,show,preview,choose,discard,restore,fix-word,caption,render}"
        in capsys.readouterr().out,
    ) == (
        0,
        True,
    )


@pytest.mark.parametrize(
    "action",
    ["list", "show", "preview", "choose", "discard", "restore", "fix-word", "caption", "render"],
)
def test_each_cut_action_help_shows_an_example_ready_to_copy(
    action: str, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = main(["cut", action, "--help"])

    assert (exit_code, f"wordcut cut {action} " in capsys.readouterr().out) == (0, True)
